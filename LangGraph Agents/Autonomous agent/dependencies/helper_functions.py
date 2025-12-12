# app/dependencies/dependency_injections.py
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from models.association      import user_group
from models.tenant           import Tenant
from models.user            import User
from models.group           import Group
from models.workflow         import Workflow
from models.ip_address       import IPAddress
from models.token_blacklist  import TokenBlacklist
from models.otp_verification import OTPVerification
from typing import Union
from dotenv import load_dotenv
import os
import logging

load_dotenv()
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

# Common helper functions
def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.error(f"JWT decoding error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

def check_token_revocation(jti: str, db: Session):
    if db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first():
        logger.warning(f"Revoked token attempted access: {jti}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked"
        )

def validate_token_payload(payload: dict):
    required_fields = ["email", "role", "id", "jti"]
    if not all(payload.get(field) for field in required_fields):
        logger.error("Token missing required fields")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token structure"
        )

def get_account_by_role(role: str, user_id: int, email: str, db: Session) -> Union[Tenant, User]:
    model_map = {
        "tenant": (Tenant, None),
        "team_member": (User, None),
        "client": (User, None),
        # "super_admin": (UnicornAdmin, "super_admin"),
        # "system_admin": (UnicornAdmin, "system_admin")
    }

    model, role_filter = model_map.get(role, (None, None))
    if not model:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role specified"
        )

    query = db.query(model).filter(
        model.id == user_id,
        model.email == email
    )
    
    if role_filter:
        query = query.filter(model.role == role_filter)
    else:
        query = query.filter(model.role == role)

    account = query.first()
    if not account:
        logger.error(f"Account not found: {role}/{email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    return account