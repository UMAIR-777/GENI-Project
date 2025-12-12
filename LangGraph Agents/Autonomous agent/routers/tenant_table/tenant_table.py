from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any
from database.session import get_db
from schemas.tenant_tables import (
    TableCreateRequest, TableResponse, TableListResponse, 
    TableDeleteResponse, TableListItem, TableRenameRequest,TableUpdateRequest
)
from models.tenant import Tenant
from dependencies import requires_tenant
import json
from utils.generate_uuid import generate_uuid
from error_handlers.utils.database_error import clean_database_error
router = APIRouter()


@router.post(
    "/",
    response_model=TableResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_table(
    request: TableCreateRequest,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db)
):
    """Create a new table in the tenant's database"""
    # Generate UUID for the new table
    new_id = generate_uuid()
    
    try:
        # Execute stored procedure to create table with the generated ID
        db.execute(
            text("SELECT create_tenant_table_with_id(:id, :tenant_id, :db_name, :table_name, :columns)"),
            {
                "id": new_id,
                "tenant_id": str(tenant.id),
                "db_name": request.database_name,
                "table_name": request.table_name,
                "columns": json.dumps(request.columns)
            }
        )
        db.commit()
        
        # Return success response with all fields including the ID
        return TableResponse(
            id=new_id,
            name=request.table_name,
            database_name=request.database_name,
            tenant_id=str(tenant.id)
        )
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = str(e)
        
        # Provide clean error messages
        if "already exists" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Table '{request.table_name}' already exists"
            )
        if "Invalid table name" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid table name format: '{request.table_name}'"
            )
        if "does not exist" in error_msg and "Database" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{request.database_name}' does not exist"
            )
            
        # For any other SQLAlchemy errors
        clean_error = clean_database_error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=clean_error
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
@router.get(
    "/{db_name}",
    response_model=TableListResponse
)
async def list_tables(
    db_name: str,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db)
):
    """List all tables in a specific database with their schema definitions"""
    try:
        # Execute the stored procedure to get detailed table information
        result = db.execute(
            text("SELECT * FROM get_tenant_tables(:tenant_id, :db_name)"),
            {"tenant_id": str(tenant.id), "db_name": db_name}
        )
        
        # Process results and include schema definitions
        tables = []
        for row in result:
            # Parse the schema definition string
            try:
                schema_definition = json.loads(row.schema_definition) if row.schema_definition else []
            except json.JSONDecodeError:
                schema_definition = []
            
            tables.append(TableListItem(
                id=row.id,
                name=row.name,
                columns=schema_definition
            ))
        
        return TableListResponse(tables=tables)
    except SQLAlchemyError as e:
        error_msg = str(e)
        
        # Specific error for database not existing
        if "does not exist" in error_msg and "Database" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{db_name}' does not exist"
            )
            
        # For any other SQLAlchemy errors
        clean_error = clean_database_error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=clean_error
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
            
@router.put(
    "/{db_name}/rename",
    response_model=TableResponse
)
async def rename_table(
    db_name: str,
    request: TableRenameRequest,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db)
):
    """Rename a table in the tenant's database"""
    try:
        # Execute the rename_tenant_table stored procedure
        result = db.execute(
            text("SELECT rename_tenant_table(:tenant_id, :db_name, :old_table_name, :new_table_name)"),
            {
                "tenant_id": str(tenant.id),
                "db_name": db_name,
                "old_table_name": request.old_table_name,
                "new_table_name": request.new_table_name
            }
        ).scalar()
        
        # Commit the transaction
        db.commit()
        
        # Get the table ID from the result
        table_id = result
        
        # Return the response with all required fields
        return TableResponse(
            id=table_id,
            name=request.new_table_name,
            database_name=db_name,
            tenant_id=str(tenant.id)
        )
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = str(e)
        
        # Specific errors for different cases
        if "does not exist" in error_msg and "Table" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{request.old_table_name}' does not exist in database '{db_name}'"
            )
        if "does not exist" in error_msg and "Database" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{db_name}' does not exist"
            )
        if "already exists" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Table '{request.new_table_name}' already exists in database '{db_name}'"
            )
        if "Invalid table name" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid table name format: '{request.new_table_name}'"
            )
            
        # For any other SQLAlchemy errors
        clean_error = clean_database_error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=clean_error
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{db_name}/{table_name}",
    response_model=TableDeleteResponse,
    status_code=status.HTTP_200_OK
)
async def delete_table(
    db_name: str,
    table_name: str,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db)
):
    """Delete a table from a database"""
    try:
        # Call the stored procedure to delete the table
        success = db.execute(
            text("SELECT delete_tenant_table(:tenant_id, :db_name, :table_name)"),
            {
                "tenant_id": str(tenant.id),
                "db_name": db_name,
                "table_name": table_name
            }
        ).scalar()
        
        db.commit()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found in database '{db_name}'"
            )
        
        return {
            "status": "success", 
            "message": f"Table '{table_name}' deleted successfully from database '{db_name}'"
        }
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = str(e)
        
        # Specific errors for different cases
        if "does not exist" in error_msg and "Table" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' does not exist in database '{db_name}'"
            )
        if "does not exist" in error_msg and "Database" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{db_name}' does not exist"
            )
            
        # For any other SQLAlchemy errors
        clean_error = clean_database_error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=clean_error
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )