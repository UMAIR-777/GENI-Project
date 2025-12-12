from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import column, text, select
from database.session import get_db
from models.tenant_database import TenantDatabase
from schemas.tenant_database import DatabaseCreateRequest, DatabaseResponse, DatabaseListResponse, SchemaListResponse, SchemaResponse
from models.tenant import Tenant
from utils.generate_uuid import generate_uuid
from dependencies import requires_tenant
from sqlalchemy.exc import SQLAlchemyError
router = APIRouter()

@router.post(
    "/",
    response_model=DatabaseResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_database(
    request: DatabaseCreateRequest,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db)
):
    new_id = generate_uuid()
    try:
        # pass new_id into SQL
        db.execute(
            text("SELECT create_tenant_database(:id, :tenant_id, :db_name)"),
            {"id": new_id, "tenant_id": str(tenant.id), "db_name": request.name}
        )
        db.commit()

        # return the record info
        row = db.execute(
            text("SELECT id, name, schema_name, tenant_id FROM tenant_databases WHERE id = :id"),
            {"id": new_id}
        ).first()

        return DatabaseResponse(
            id=row.id,
            name=row.name,
            schema_name=row.schema_name,
            tenant_id=row.tenant_id
        )
    except Exception as e:
        db.rollback()
        msg = str(e)
        if "Invalid database name" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg
        )


# @router.get(
#     "/",
#     response_model=DatabaseListResponse
# )
# async def list_schemas(
#     tenant: Tenant = Depends(requires_tenant),
#     db: Session = Depends(get_db)
# ):
#     try:
#         query = text("""
#             SELECT * FROM get_tenant_schemas(:tenant_id)
#         """).columns(
#             column('schema_name')
#         )
#         result = db.execute(query, {"tenant_id": str(tenant.id)})
#         rows = result.fetchall()

#         return SchemaListResponse(
#             schemas=[SchemaResponse(schema_name=row[0]) for row in rows]
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error retrieving schemas: {str(e)}"
#         )

@router.get(
    "/",
    response_model=DatabaseListResponse
)
async def list_databases(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db)
):
    try:
        # Directly query the table using SQLAlchemy ORM
        databases = db.query(TenantDatabase).filter(
            TenantDatabase.tenant_id == str(tenant.id)
        ).all()
        
        results = [
            DatabaseResponse(
                id=db.id,
                name=db.name,
                schema_name=db.schema_name,
                tenant_id=db.tenant_id
            ) for db in databases
        ]
        return DatabaseListResponse(databases=results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving databases: {str(e)}"
        )

@router.put(
    "/{old_name}",
    response_model=DatabaseResponse
)
async def rename_database(
    old_name: str,
    request: DatabaseCreateRequest,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db)
):
    try:
        db.execute(
            text("SELECT rename_tenant_database(:tenant_id, :old_name, :new_name)"),
            {"tenant_id": str(tenant.id), "old_name": old_name, "new_name": request.name}
        )
        db.commit()
        
        # return updated record
        row = db.execute(
            text("SELECT id, schema_name FROM tenant_databases WHERE tenant_id=:t AND name=:n"),
            {"t": str(tenant.id), "n": request.name}
        ).first()
        
        if not row:
            raise Exception(f"Database '{request.name}' not found after rename operation")
            
        return DatabaseResponse(
            id=row.id,
            name=request.name,
            schema_name=row.schema_name,
            tenant_id=tenant.id
        )
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = str(e)
        
        # Extract the actual error message
        if "psycopg2.errors.RaiseException" in error_msg:
            import re
            match = re.search(r'RaiseException\) (.+?)(?:\nCONTEXT|\n\[SQL)', error_msg)
            if match:
                error_msg = match.group(1).strip()
        
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                              detail=f"Database '{old_name}' not found")
        if "invalid database name" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                              detail=f"Invalid database name: '{request.name}'")
        if "already exists" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                              detail=f"Database '{request.name}' already exists")
            
        # For any other error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                          detail=f"Database error: {error_msg}")
                          
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                          detail=str(e))
    
@router.delete(
    "/{db_name}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_database(
    db_name: str,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db)
):
    try:
        db.execute(
            text("SELECT delete_tenant_database(:tenant_id, :db_name)"),
            {"tenant_id": str(tenant.id), "db_name": db_name}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )