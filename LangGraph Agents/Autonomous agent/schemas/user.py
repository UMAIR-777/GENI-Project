from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional


# ──────────────────────────────────────────────────────────────
# USER SCHEMAS
# ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name      : str              = Field(..., description="Full name of the user")
    email     : EmailStr         = Field(..., description="User's email address")
    password  : str              = Field(..., description="Password for the user account")
    role      : str              = Field(..., description="Role assigned to the user")
    group_ids : List[str] = Field(default_factory=list, description="List of associated group IDs")


class UserResponse(BaseModel):
    id        : str              = Field(..., description="Unique identifier of the user")
    email     : EmailStr         = Field(..., description="User's email address")
    role      : str              = Field(..., description="User's role")
    is_active : bool             = Field(..., description="User's activation status")

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email     : Optional[EmailStr] = Field(None, description="New email address")
    password  : Optional[str]      = Field(None, description="New password")
    role      : Optional[str]      = Field(None, description="New role for the user")
    is_active : Optional[bool]     = Field(None, description="Activation status")


class UserDetailResponse(BaseModel):
    id        : str              = Field(..., description="Unique identifier of the user")
    email     : EmailStr         = Field(..., description="User's email address")
    role      : str              = Field(..., description="User's role")
    is_active : bool             = Field(..., description="User's activation status")
    groups     : List[str]        = Field(..., description="List of group names the user belongs to")
    workflows : List[str]        = Field(..., description="List of workflow names associated with the user")

    class Config:
        from_attributes = True


class AssignWorkflowAccessRequest(BaseModel):
    workflow_ids: List[str]


class UserUpdateRequest(BaseModel):
    pass
