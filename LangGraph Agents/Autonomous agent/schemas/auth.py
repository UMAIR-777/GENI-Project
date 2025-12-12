from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

# ──────────────────────────────────────────────────────────────
# TOKEN SCHEMAS
# ──────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type  : str = Field(..., description="Type of token, typically 'bearer'")


# ──────────────────────────────────────────────────────────────
# OTP VERIFICATION & LOGIN SCHEMAS
# ──────────────────────────────────────────────────────────────
class OTPVerificationRequest(BaseModel):
    email  : EmailStr = Field(..., description="User's email address")
    otp    : str      = Field(..., description="One-time password for verification")
    purpose: Literal['register', 'super_admin_register'] = Field(
        ..., description="Purpose of OTP (e.g., user registration or admin registration)"
    )

class OTPLoginInitiate(BaseModel):
    email   : EmailStr = Field(..., description="Registered email address")
    password: str      = Field(..., description="User's login password")


# ──────────────────────────────────────────────────────────────
# IP ADDRESS SCHEMAS
# ──────────────────────────────────────────────────────────────
class IPAddressCreate(BaseModel):
    email: EmailStr = Field(..., description="Email associated with the IP")
    ip   : str      = Field(..., description="Client's IP address")

class IPAddressResponse(BaseModel):
    email     : str      = Field(..., description="Email associated with the IP")
    ip        : str      = Field(..., description="Recorded IP address")
    created_at: datetime = Field(..., description="Timestamp when IP was recorded")

    class Config:
        from_attributes = True
