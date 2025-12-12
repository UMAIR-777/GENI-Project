from pydantic import BaseModel
from typing import List

class DatabaseResponse(BaseModel):
    database_id: str  
    name: str  
    
    
class DatabaseListResponse(BaseModel):
    databases: List[DatabaseResponse]

class DatabaseCreateRequest(BaseModel):
    name: str

class DatabaseRenameRequest(BaseModel):
    new_name: str
    current_name: str