from typing import Optional
from pydantic            import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: str 
    password: str

class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    # add any other fields your service returns

class ValidateTokenResponse(BaseModel):
    valid: bool
    user: Optional[UserOut] = None