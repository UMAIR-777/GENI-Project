from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class JWTCreateRequest(BaseModel):
    workflow_id: str
    expires_in: int = Field(..., gt=0, description="Expiration in seconds")

class JWTCreateResponse(BaseModel):
    token: str
    expires_at: datetime

class PublicAuthResult(BaseModel):
    tenant_id: str
    workflow_id: str
    api_key_id: Optional[str] = None
    jwt_jti: Optional[str] = None
    jwt_sub: Optional[str] = None

class ExecuteResponse(BaseModel):
    status: str
    data: dict
