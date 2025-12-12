import traceback
from fastapi import APIRouter, Depends, Body, HTTPException, status, Request
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from utils.generate_uuid import generate_uuid
from schemas.public_access_workflow.workflow_api_key import KeyCreateRequest, KeyCreateResponse
from schemas.public_access_workflow.workflow_jwt_token import JWTCreateRequest, JWTCreateResponse, ExecuteResponse
from service.public_access_workflow.workflow_api_key import generate_api_key
from service.public_access_workflow.workflow_jwt_token import create_jwt
from dependencies.public_access_workflow.dependencies import public_auth
from database.session import get_db
from models.workflow_api_key import APIKey, APIKeyStatus
from models.workflow_jwt_token import JWTToken
# from app.models.workflow import Workflow
from models.workflow_audit_log import AuditLog

router = APIRouter()

def execute_workflow_logic(config: dict, payload: dict) -> dict:
    # Replace with your real orchestration logic
    # For example, dispatch tasks to Celery, step through nodes, etc.
    return {"status": "success", "data": payload}



@router.post("/auth/api-key", response_model=KeyCreateResponse)
def create_api_key(
    req: KeyCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        raw, hashed = generate_api_key()
        obj = APIKey(
            id=generate_uuid(),
            workflow_id=req.workflow_id,
            key_hash=hashed,
            description=req.description,
            status=APIKeyStatus.ACTIVE
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return KeyCreateResponse(
            id=obj.id,
            api_key=raw,
            workflow_id=obj.workflow_id,
            description=obj.description
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.post("/auth/jwt", response_model=JWTCreateResponse)
def create_jwt_token(
    req: JWTCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        jti = generate_uuid()
        expires_at = datetime.utcnow() + timedelta(seconds=req.expires_in)
        token = create_jwt(
            tenant_id=generate_uuid(),
            workflow_id=str(req.workflow_id),
            sub="system",
            expires_delta=timedelta(seconds=req.expires_in),
            jti=jti,
        )
        rec = JWTToken(
            id = generate_uuid(),
            # tenant_id=generate_uuid(),
            workflow_id=req.workflow_id,
            jti=jti,
            expires_at=expires_at,
        )
        db.add(rec); db.commit()
        return JWTCreateResponse(token=token, expires_at=expires_at)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

# @router.post("/executer", response_model=ExecuteResponse, dependencies=[Depends(lambda request: request.app.state.limiter.limit("10/minute"))])
# def execute_workflow(
#     request: Request,
#     auth=Depends(public_auth),
#     payload: dict = Body(...),
#     db: Session = Depends(get_db),
# ):
#     # wf = db.query(Workflow).filter_by(id=auth.workflow_id, tenant_id=auth.tenant_id).first()
#     # if not wf:
#     #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

#     # Run service
#     result = execute_workflow_logic({}, payload)

#     # Audit
#     log = AuditLog(
#         tenant_id=auth.tenant_id,
#         workflow_id=auth.workflow_id,
#         api_key_id=auth.api_key_id,
#         jwt_jti=auth.jwt_jti,
#         jwt_sub=auth.jwt_sub,
#         client_ip=request.client.host,
#         user_agent=request.headers.get("user-agent"),
#         request_payload=payload,
#         response_payload=result,
#         status_code=str(200),
#     )
#     db.add(log); db.commit()

#     return ExecuteResponse(status=result["status"], data=result["data"])
