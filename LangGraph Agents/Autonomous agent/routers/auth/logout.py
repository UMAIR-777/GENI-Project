from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from datetime import datetime

from models.tenant import Tenant
from models.user import User
from database.session import get_db
from utils.generate_uuid import generate_uuid
from dependencies.dependency_injections import get_account_details, security
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter()

@router.post("/logout")
async def logout(
    account: Tenant | User = Depends(get_account_details),
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        token = credentials.credentials
        payload = jwt.get_unverified_claims(token)
        jti = payload.get("jti")
        exp = datetime.utcfromtimestamp(payload.get("exp"))

        # Blacklist the token via stored procedure
        bl_id = generate_uuid()
        db.execute(
            text(
                "CALL sp_insert_token_blacklist(:id, :jti, :email, :exp, :account_id, :account_type);"
            ),
            {
                "id": bl_id,
                "jti": jti,
                "email": account.email,
                "exp": exp,
                "account_id": account.id,
                "account_type": type(account).__name__.lower()
            }
        )

        # Remove IP addresses via stored procedures
        if isinstance(account, Tenant):
            db.execute(
                text("CALL sp_delete_ip_by_tenant(:tenant_id);"),
                {"tenant_id": account.id}
            )
        elif isinstance(account, User):
            db.execute(
                text("CALL sp_delete_ip_by_user(:user_id);"),
                {"user_id": account.id}
            )
        elif isinstance(account, UnicornAdmin):
            db.execute(
                text("CALL sp_delete_ip_by_admin(:admin_id);"),
                {"admin_id": account.id}
            )
        else:
            raise HTTPException(status_code=400, detail="Unknown account type")

        db.commit()
        return {"message": "Successfully logged out"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout failed: {str(e)}"
        )