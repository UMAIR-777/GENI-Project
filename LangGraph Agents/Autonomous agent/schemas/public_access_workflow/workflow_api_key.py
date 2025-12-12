from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class KeyCreateRequest(BaseModel):
    workflow_id: str
    description: Optional[str] = None

class KeyCreateResponse(BaseModel):
    id: str
    api_key: str
    workflow_id: str
    description: Optional[str]
