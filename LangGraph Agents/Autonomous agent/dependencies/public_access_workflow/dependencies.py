from fastapi import Depends, HTTPException, Request, status
from typing import Optional
from sqlalchemy.orm import Session
from utils.generate_uuid import generate_uuid
from service.public_access_workflow.workflow_api_key import get_api_key_auth
from service.public_access_workflow.workflow_jwt_token import get_jwt_auth
from schemas.public_access_workflow.workflow_jwt_token import PublicAuthResult
from database.session import get_db

async def public_auth(
    request: Request,
    api_key_obj = Depends(get_api_key_auth),
    jwt_payload: Optional[dict] = Depends(lambda token=Depends(get_jwt_auth), db=Depends(get_db): get_jwt_auth(token, db)),
) -> PublicAuthResult:
    # exactly one method
    if (api_key_obj is None) == (jwt_payload is None):
        code = status.HTTP_400_BAD_REQUEST if api_key_obj and jwt_payload else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=code, detail="Provide exactly one of api_key or Bearer token")
    if api_key_obj:
        return PublicAuthResult(
            tenant_id=api_key_obj.tenant_id,
            workflow_id=api_key_obj.workflow_id,
            api_key_id=api_key_obj.id,
        )
    # JWT path
    if "workflow:execute" not in jwt_payload.get("scope", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing required scope")
    return PublicAuthResult(
        tenant_id=generate_uuid()(jwt_payload["tid"]),
        workflow_id=generate_uuid()(jwt_payload["wid"]),
        jwt_jti=jwt_payload["jti"],
        jwt_sub=jwt_payload["sub"],
    )
