from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Union
from dotenv import load_dotenv
import logging

from database.session import get_db
from models.association      import user_group
from models.tenant           import Tenant
from models.user            import User
from models.group           import Group
from models.workflow         import Workflow
from models.ip_address       import IPAddress
from models.token_blacklist  import TokenBlacklist
from models.otp_verification import OTPVerification
from dependencies.helper_functions import check_token_revocation, decode_token, get_account_by_role, validate_token_payload

load_dotenv()
logger = logging.getLogger(__name__)

security = HTTPBearer()

# Main dependency functions
def get_tenant_or_team_member(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = decode_token(token)
    validate_token_payload(payload)
    check_token_revocation(payload['jti'], db)

    role = payload['role']
    logger.debug(f"Attempting access as {role}")

    if role == "client":
        logger.warning("Client role attempted unauthorized access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client role not authorized"
        )

    return get_account_by_role(
        role=role,
        user_id=payload['id'],
        email=payload['email'],
        db=db
    )

def get_account_details(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Union[Tenant, User]:
    token = credentials.credentials
    payload = decode_token(token)
    validate_token_payload(payload)
    check_token_revocation(payload['jti'], db)

    return get_account_by_role(
        role=payload['role'],
        user_id=payload['id'],
        email=payload['email'],
        db=db
    )

def base_auth_dependency(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
    expected_role: str = None,
    model_class = None
):
    token = credentials.credentials
    payload = decode_token(token)
    check_token_revocation(payload.get('jti'), db)
    
    email = payload.get('email')
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    if expected_role and payload.get('role') != expected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid permissions"
        )

    account = db.query(model_class).filter(
        model_class.email == email
    ).first()

    if not account or (hasattr(account, 'is_active') and not account.is_active):
        logger.error(f"Account not found or inactive: {email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return account

# Specific role dependencies
def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    return base_auth_dependency(
        credentials=credentials,
        db=db,
        expected_role="tenant",
        model_class=Tenant
    )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    return base_auth_dependency(
        credentials=credentials,
        db=db,
        model_class=User
    )

def get_current_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    payload = decode_token(credentials.credentials)
    check_token_revocation(payload.get('jti'), db)
    
    email = payload.get('email')
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return email