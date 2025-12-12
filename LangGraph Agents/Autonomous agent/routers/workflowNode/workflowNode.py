import traceback
from fastapi                import APIRouter, Depends, HTTPException, logger
from sqlalchemy             import text
from sqlalchemy.orm         import Session
from sqlalchemy.exc         import IntegrityError, DBAPIError
from typing                 import Union
import json
from sqlalchemy import cast
from fastapi import status

from database.session       import get_db
from dependencies           import requires_tenant_or_team_member
from utils.generate_uuid    import generate_uuid
from models.tenant          import Tenant
from models.user            import User
from schemas.workflowNode   import (
                                WorkflowNodeAgentRequest, 
                                WorkflowNodeCreateRequest,
                                WorkflowNodeCreateResponse,
                                WorkflowNodeDeleteResponse,
                                WorkflowNodeListItem,      
                                WorkflowNodeListResponse,  
                                WorkflowNodeReadResponse,  
                                WorkflowNodeResponse,      
                                WorkflowNodeUpdate          
                            )
from utils.ip_verifier      import verify_ip
from utils.bucket_operation import upload_node_code_to_bucket
from workflow.embedding_service import EmbeddingService


from dependencies            import requires_tenant


from dotenv import load_dotenv
load_dotenv()

from workflow.embedding_service import EmbeddingService

embed_svc = EmbeddingService()





router = APIRouter()

@router.post("/agent", response_model=dict)
async def node_agent_endpoint(
    request: WorkflowNodeAgentRequest,
    user: Union[Tenant, User] = Depends(requires_tenant_or_team_member),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    # Existing agent implementation
    pass

@router.post("/", response_model=WorkflowNodeCreateResponse, status_code=201)
async def create_node(
    payload: WorkflowNodeCreateRequest,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip),
):
    # 1) Generate ID & tenant
    gen_uuid = generate_uuid()
    tenant_id = tenant.id if isinstance(tenant, Tenant) else tenant.tenant_id

    # 2) Ensure URI present
    if not payload.uri:
        print("Validation error: missing URI")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="URI is required for node creation")

    # 3) Prepare params
    params = {
        "p_id": gen_uuid,
        "p_code": payload.code,
        "p_tenant_id": tenant_id,
        "p_name": payload.name,
        "p_input": json.dumps(payload.input, ensure_ascii=False),
        "p_output": json.dumps(payload.output, ensure_ascii=False),
        "p_tags": json.dumps(payload.tags, ensure_ascii=False),
        "p_description": payload.description,
        "p_spo": json.dumps(payload.spo, ensure_ascii=False),
        "p_node_metadata": json.dumps({"code_uri": payload.uri}, ensure_ascii=False)
    }

    # 4) Call the stored procedure WITHOUT casts
    sql = text("""
    SELECT * FROM workflownode_create(
       :p_id,
       :p_code,
       :p_tenant_id,
       :p_name,
       :p_input,
       :p_output,
       :p_tags,
       :p_description,
       :p_spo,
       :p_node_metadata
    )
    """)
    try:
        print(f"DB DEBUG: executing workflownode_create with params {params}")
        result = db.execute(sql, params).fetchone()
        db.commit()
        print(f"DB DEBUG: commit succeeded, result = {result}")
    except IntegrityError as ie:
        db.rollback()
        print(f"DB DEBUG: IntegrityError: {ie}")
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Node with this name already exists")
    except Exception as e:
        db.rollback()
        print(f"DB DEBUG: unexpected DB error: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database execution failed: {e}")

    # 5) Build node_dict for embeddings
    node_dict = {
        "id": gen_uuid,
        "input": payload.input,
        "output": payload.output,
        "tags": payload.tags,
        "description": [payload.description],
        "spo": payload.spo,
        "uri": payload.uri
    }


    # 6) Generate embeddings (non‐blocking)
    try:
        print(f"EMBED DEBUG: starting embeddings for node {gen_uuid}")
        count = embed_svc.generate_and_store_node_embeddings([node_dict])
        print(f"EMBED DEBUG: embeddings succeeded, {count} rows stored")
    except Exception as e:
        print(f"EMBED DEBUG: embeddings failed: {e}")
        # continue without failing the request

    # 7) Return to caller
    return WorkflowNodeCreateResponse(id=result[0], name=result[1])


@router.get("/{node_id}", response_model=WorkflowNodeReadResponse)
async def read_node(
    node_id: str,
    current_user: Union[Tenant, User] = Depends(requires_tenant_or_team_member),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    tenant_id = current_user.id if isinstance(current_user, Tenant) else current_user.tenant_id

    try:
        result = db.execute(
            text("SELECT * FROM workflownode_get_by_id(:node_id, :tenant_id)"),
            {"node_id": node_id, "tenant_id": tenant_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Node not found")

        return WorkflowNodeReadResponse(
            id=result.id,
            name=result.name,
            code_uri=result.code_uri,
            metadata=result.metadata
        )

    except DBAPIError as e:
        db.rollback()
        print(f"DATABASE ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e.orig)}")

    except Exception as e:
        db.rollback()
        print(f"INTERNAL SERVER ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{node_id}", response_model=WorkflowNodeResponse)
async def update_node(
    node_id: str,
    update_data: WorkflowNodeUpdate,
    user: Union[Tenant, User] = Depends(requires_tenant_or_team_member),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    tenant_id = user.id if isinstance(user, Tenant) else user.tenant_id

    try:
        print(f"DEBUG: Updating node {node_id} for tenant {tenant_id}")

        # Convert Pydantic model to JSON strings where needed
        params = {
            "p_node_id": node_id,
            "p_tenant_id": tenant_id,
            "p_code": update_data.code,
            "p_input": json.dumps(update_data.input),
            "p_output": json.dumps(update_data.output),
            "p_tags": json.dumps(update_data.tags),
            "p_description": update_data.description,
            "p_spo": json.dumps(update_data.spo),
            "p_node_metadata": json.dumps({"code_uri": update_data.uri})
        }

        result = db.execute(
            text("""
                SELECT * FROM workflownode_update(
                    :p_node_id,
                    :p_tenant_id,
                    :p_code,
                    :p_input,
                    :p_output,
                    :p_tags,
                    :p_description,
                    :p_spo,
                    :p_node_metadata
                )
            """),
            params
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found or unauthorized"
            )

        db.commit()
        print(f"DEBUG: Successfully updated node {node_id}")

        # Fetch updated node details
        updated_row = db.execute(
            text("""
                SELECT 
                    id, 
                    name, 
                    node_metadata->>'code_uri' AS uri,
                    node_metadata,
                    updated_at 
                FROM nodes 
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            {"id": node_id, "tenant_id": tenant_id}
        ).fetchone()

        if not updated_row:
            raise HTTPException(status_code=404, detail="Node not found")

        # Safe conversion to dict
        node_data = dict(updated_row._mapping)  # or .items() on older versions

        return WorkflowNodeResponse(**node_data)

    except DBAPIError as e:
        db.rollback()
        print(f"DATABASE ERROR: {str(e)}")
        print(traceback.format_exc())
        orig_error = str(e.orig) if hasattr(e, "orig") else str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {orig_error}"
        )

    except Exception as e:
        db.rollback()
        print(f"INTERNAL SERVER ERROR: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.delete("/{node_id}", response_model=WorkflowNodeDeleteResponse)
async def delete_node(
    node_id: str,
    current_user: Union[Tenant, User] = Depends(requires_tenant_or_team_member),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    tenant_id = current_user.id if isinstance(current_user, Tenant) else current_user.tenant_id
    try:
        db.execute(
            text("CALL workflownode_delete(:node_id, :tenant_id)"),
            {"node_id": node_id, "tenant_id": tenant_id}
        )
        db.commit()
    except DBAPIError as e:
        db.rollback()
        print(f"DATABASE ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e.orig)}")

    except Exception as e:
        db.rollback()
        print(f"INTERNAL SERVER ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    return WorkflowNodeDeleteResponse(message="Node deleted successfully")

@router.get("/", response_model=WorkflowNodeListResponse)
async def get_all_nodes(
    current_user: Union[Tenant, User] = Depends(requires_tenant_or_team_member),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    try:
        # Resolve tenant ID
        tenant_id = current_user.id if isinstance(current_user, Tenant) else current_user.tenant_id
        print(f"DEBUG: Fetching all nodes for tenant ID: {tenant_id}")

        # Call the PostgreSQL function using SQLAlchemy
        result_proxy = db.execute(
            text("SELECT * FROM workflownode_list(:p_tenant_id)"),
            {
                "p_tenant_id": tenant_id
            }
        )

        # Get all results
        results = result_proxy.fetchall()

        # Map results to Pydantic model
        node_items = [
            WorkflowNodeListItem(
                id=row.id,
                name=row.name,
                code_uri=row.code_uri,
                metadata=row.metadata
            )
            for row in results
        ]

        return WorkflowNodeListResponse(nodes=node_items)

    except DBAPIError as e:
        db.rollback()
        print(f"DATABASE ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e.orig)}")

    except Exception as e:
        db.rollback()
        print(f"INTERNAL SERVER ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")