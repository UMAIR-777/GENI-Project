from pydantic import BaseModel
from typing import List, Optional

class DatabaseCreateRequest(BaseModel):
    name: str

# schemas.py
class DatabaseResponse(BaseModel):
    id: str
    name: str
    schema_name: str
    tenant_id: str

class DatabaseListResponse(BaseModel):
    databases: List[DatabaseResponse]

class SchemaResponse(BaseModel):
    schema_name: str

class SchemaListResponse(BaseModel):
    schemas: List[SchemaResponse]

