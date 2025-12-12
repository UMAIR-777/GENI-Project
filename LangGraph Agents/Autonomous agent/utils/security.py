from typing                         import Union
from passlib.context                import CryptContext
from datetime                       import datetime, timedelta
from jose                           import JWTError, jwt as jose_jwt
from fastapi                        import HTTPException, status
from models.tenant                  import Tenant
from models.user                    import User
from utils.config                   import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from sqlalchemy.orm                 import Session
from .generate_uuid                 import generate_uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "jti": generate_uuid(),  # Add unique token identifier
        "exp": expire
    })
    return jose_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_account(email: str, password: str, db: Session) -> Union[Tenant, User]:
    # Check in order of privilege: tenant -> user
    account = db.query(Tenant).filter(Tenant.email == email).first()
    if account:
        if verify_password(password, account.hashed_password):
            return account
        raise HTTPException(status_code=400, detail="Invalid password")
    
    account = db.query(User).filter(User.email == email).first()
    if account:
        if verify_password(password, account.hashed_password):
            return account
        raise HTTPException(status_code=400, detail="Invalid password")
    
    raise HTTPException(status_code=404, detail="Account not found")