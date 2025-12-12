import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import time
from fastapi import APIRouter, Depends, HTTPException, Path, logger, status, Query
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from code_executor.common import InvalidInputError
from database.session import get_db
from utils.generate_uuid import generate_uuid
from models.tenant import Tenant
from models.user import User
from models.workflow import Workflow
from code_executor.agent import create_workflow_agent
from schemas.workflow import *
from pgvector.sqlalchemy import Vector

from dependencies import requires_tenant_or_team_member, requires_tenant_or_team_member_or_client
from typing import Dict, List, Optional
from utils.ip_verifier import verify_ip
from typing import Union
import json
from workflow.embedding_service import EmbeddingService
from workflow_runner.runWorkflow import run_Workflow
import logging

dlogger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
embed=EmbeddingService()
from dependencies import requires_tenant
router = APIRouter()
# Agent-generated workflow
@router.post("/agent", response_model=WorkflowCreateResponse)
def workflow_agent_endpoint(
    workflow_req: WorkflowCreateRequest,
    user: Union[Tenant, User] = Depends(requires_tenant_or_team_member),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
):
    try:
        logger.info("Agent request task=%s by user=%s", workflow_req.task, user.id)
        data = create_workflow_agent(workflow_req.task)
        return WorkflowCreateResponse(workflow=data)
    except InvalidInputError as e:
        logger.error("Invalid input: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Agent endpoint failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent processing error")

# Create workflow
@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip),
):
    try:
        # ensure dict
        data = payload.data if isinstance(payload.data, dict) else json.loads(payload.data)
        new_id = generate_uuid()
        
        # Generate embedding text from available metadata
        embedding_text = ""
        if payload.user_task:
            embedding_text += f"User Task: {payload.user_task}\n"
        if payload.descriptions:
            embedding_text += f"Descriptions: {' '.join(payload.descriptions)}\n"
        if payload.tags:
            embedding_text += f"Tags: {' '.join(payload.tags)}\n"
        if payload.spo:
            embedding_text += f"SPO: {json.dumps(payload.spo)}\n"
        
        # If no explicit metadata, use workflow name and data as fallback
        if not embedding_text.strip():
            embedding_text = f"{payload.name}: {json.dumps(data)}"
        
        # Generate and normalize embedding
        embedding = None
        if embedding_text.strip():
            try:
                raw_embedding = embed.embed_texts([embedding_text])
                
                # Handle both numpy arrays and regular lists
                if hasattr(raw_embedding[0], 'tolist'):  # numpy array
                    normalized = embed.normalize_embedding(raw_embedding[0])
                    embedding = normalized.tolist()
                else:  # already a list
                    embedding = embed.normalize_embedding(raw_embedding[0])
                    
                # Validate the embedding format
                if not isinstance(embedding, list):
                    logger.error(f"Unexpected embedding format: {type(embedding)}")
                    embedding = None
                    
            except Exception as e:
                logger.error(f"Failed to generate workflow embedding: {str(e)}", exc_info=True)
                # Continue without embedding if generation fails

        # Convert embedding to PostgreSQL vector format string
        embedding_str = None
        if embedding:
            try:
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            except Exception as e:
                logger.error(f"Failed to format embedding: {str(e)}")
        
        # Create workflow with embedding
        stmt = text(
            "CALL public.sp_create_workflow(:id, :name, :data, :tenant_id, :is_public, :version, :embedding)"
        )
        params = {
            "id": new_id,
            "name": payload.name,
            "data": json.dumps(data),
            "tenant_id": tenant.id,
            "is_public": payload.is_public,
            "version": 1,
            "embedding": embedding_str
        }
        db.execute(stmt, params)
        db.commit()
        
        return WorkflowResponse(
            id=new_id,
            name=payload.name,
            data=data,
            tenant_id=tenant.id,
            is_public=payload.is_public,
            version=1
        )
        
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON data")
    except DBAPIError as e:
        logger.error("DB error create: %s", e.orig)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    


# Update workflow
@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    user: Union[Tenant, User] = Depends(requires_tenant_or_team_member),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
):
    try:
        # Parse data safely
        data = payload.data if isinstance(payload.data, dict) else json.loads(payload.data)
        logger.info("Updating workflow: %s, version: %d", workflow_id, payload.version)

        # Call function without ::json in SQL string
        stmt = text("SELECT * FROM public.fn_update_workflow(:id, :data, :version)")
        params = {
            "id": workflow_id,
            "data": json.dumps(data),  # Pass as string
            "version": payload.version
        }

        row = db.execute(stmt, params).mappings().first()
        db.commit()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

        return WorkflowResponse(
            **{
                **row,
                "id": str(row["id"]),
                "data": data,
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }
        )
    except json.JSONDecodeError as je:
        logger.error("JSON decode error: %s", je)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON data")
    except DBAPIError as de:
        logger.error("DB error update: %s", de.orig, exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except Exception as e:
        logger.error("Unexpected error during workflow update: %s", e, exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# Delete workflow
@router.delete("/{workflow_id}", status_code=status.HTTP_200_OK)
def delete_workflow(
    workflow_id: str,
    user: Union[Tenant, User] = Depends(requires_tenant_or_team_member),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
):
    """
    Delete a workflow by ID.
    Returns 200 OK with success message on successful deletion.
    """
    try:
        result = db.execute(text("CALL public.sp_delete_workflow(:id)"), {"id": workflow_id})
        db.commit()
        return {"message": f"Workflow {workflow_id} deleted successfully"}
    except DBAPIError as e:
        logger.error("DB error delete: %s", e.orig)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )

# Get single workflow
@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    user: Union[Tenant, User] = Depends(requires_tenant_or_team_member_or_client),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
) -> WorkflowResponse:
    try:
        stmt = text("SELECT * FROM public.fn_get_workflow_by_id(:id)")
        row = db.execute(stmt, {"id": workflow_id}).mappings().first()
    except DBAPIError as e:
        dlogger.error("DB error on fn_get_workflow_by_id: %s", e.orig)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e.orig))

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
    return WorkflowResponse(
        id=str(row["id"]),
        name=row["name"],
        data=data,
        tenant_id=str(row["tenant_id"]),
        is_public=row["is_public"],
        version=row["version"],
        group_id=str(row["group_id"]) if row["group_id"] else None,
        created_at=row["created_at"].isoformat() if row["created_at"] else None,
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else None
    )

@router.get("", response_model=List[WorkflowResponse])
def list_workflows(
    user: Union[Tenant, User] = Depends(requires_tenant_or_team_member_or_client),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
) -> List[WorkflowResponse]:
    """List all workflows for the tenant or user using stored procedures."""
    try:
        if user.role == "tenant":
            # Use tenant function
            stmt = text("SELECT * FROM public.fn_get_all_workflows_tenant(:tenant_id)")
            params = {"tenant_id": user.id}
        else:
            # Use user function
            stmt = text("SELECT * FROM public.fn_get_all_workflows_user(:user_id)")
            params = {"user_id": user.id}

        rows = db.execute(stmt, params).mappings().all()
        dlogger.info("Retrieved %d workflows for user/tenant %s", len(rows), user.id)

    except DBAPIError as e:
        dlogger.error("DB error listing workflows: %s", e.orig)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e.orig))

    workflows: List[WorkflowResponse] = []
    for r in rows:
        try:
            raw = r["data"]
            data = json.loads(raw) if isinstance(raw, str) else raw
            workflows.append(WorkflowResponse(
                id=str(r["id"]),
                name=r["name"],
                data=data,
                tenant_id=str(r["tenant_id"]),
                is_public=r["is_public"],
                version=r["version"],
                group_id=None,  # Not returned by function
                created_at=None,  # Not returned by function
                updated_at=None   # Not returned by function
            ))
        except Exception as e:
            dlogger.error("Error mapping workflow row %s: %s", r, e)

    return workflows

@router.post("/execute-workflow/{workflow_id}", response_model=WorkflowExecuteResponse)
def execute_workflow(
    payload: WorkflowExecuteRequest,
    workflow_id: str,
    user: Union[Tenant, User] = Depends(requires_tenant_or_team_member_or_client),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip) 
):
    start_time = time.time()  
    try:
        if isinstance(user, Tenant):
            tenant_id = user.id
        else:
            tenant_id = user.tenant_id

        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(404, detail="Tenant not found.")
        bucket_uri = tenant.tenant_nodes_bucket

        workflow = db.query(Workflow).filter(
            Workflow.tenant_id == tenant_id, Workflow.id == workflow_id).first()
        if not tenant:
            raise HTTPException(404, detail="Workflow not found.")

        result = run_Workflow(
            input = payload.input,
            input_json=workflow.workflow,
            bucket_name=bucket_uri,
        )
        execution_time = time.time() - start_time
    
        return WorkflowExecuteResponse(
            message="Workflow executed successfully",
            result=result, 
            execution_time=execution_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {e}")