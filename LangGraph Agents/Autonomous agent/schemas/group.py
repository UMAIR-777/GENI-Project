# ============================ Imports ============================
from datetime            import datetime
from typing              import List, Optional
from pydantic            import BaseModel


# ============================ Schemas =============================

class GroupCreate(BaseModel):
    name: str


class GroupResponse(BaseModel):
    id   : str
    name : str

    class Config:
        from_attributes = True


class AssignWorkflowAccessRequest(BaseModel):
    workflow_ids: List[str]


class AssignGroupRequest(BaseModel):
    group_ids: List[str]


class UserWithgroupResponse(BaseModel):
    id        : str
    email     : str
    role      : str
    is_active : bool
    group    : List[str]

    class Config:
        from_attributes = True


class AssignUserToGroupRequest(BaseModel):
    user_id: str


class AssignWorkflowToGroupRequest(BaseModel):
    workflow_id: str


class GroupSpecificWorkflow(BaseModel):
    id           : str
    name         : str
    tenant_id    : str
    user_id      : Optional[str]
    group_id     : Optional[str]
    workflow     : dict
    descriptions : Optional[str]
    is_public    : bool

    class Config:
        from_attributes = True