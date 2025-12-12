from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict


# ──────────────────────────────────────────────────────────────
# DASHBOARD SCHEMAS
# ──────────────────────────────────────────────────────────────

class DashboardUserStatus(BaseModel):
    email          : str        = Field(..., description="User's email address")
    role           : str        = Field(..., description="User's role within the tenant")
    group         : List[str]  = Field(..., description="List of group names the user belongs to")
    workflow_count : int        = Field(..., description="Total number of workflows assigned to user")


class AdminDashboardStats(BaseModel):
    tenant_id         : str            = Field(..., description="Unique identifier of the tenant")
    tenant_name       : str            = Field(..., description="Name of the tenant")
    tenant_email      : EmailStr       = Field(..., description="Email address of the tenant")
    total_users       : int            = Field(..., description="Total number of user under the tenant")
    total_groups      : int            = Field(..., description="Total number of group under the tenant")
    total_workflows   : int            = Field(..., description="Total number of workflows under the tenant")
    workflows_by_group: Dict[str, int] = Field(..., description="Mapping of group name to workflow count")
