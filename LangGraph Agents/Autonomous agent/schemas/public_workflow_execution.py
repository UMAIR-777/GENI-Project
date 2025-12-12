from datetime import datetime
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class GenerateKeyResponse(BaseModel):
    api_key: str = Field(..., description="prefix.secret")
    workflow_id: str

class JWTResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class ExecutePayload(BaseModel):
    api_key: str

class ExecuteResult(BaseModel):
    status: str
    output: Optional[Dict[str, Any]]