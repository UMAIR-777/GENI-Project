from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────────────────────────────────────────
# TENANT SCHEMAS
# ──────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name     : str     = Field(..., description="Name of the tenant")
    email    : EmailStr = Field(..., description="Email address associated with the tenant")
    password : str     = Field(..., description="Password for the tenant account")


class TenantResponse(BaseModel):
    id   : str = Field(..., description="Unique identifier of the tenant")
    name : str = Field(..., description="Name of the tenant")

    class Config:
        from_attributes = True
