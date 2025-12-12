from fastapi                 import APIRouter, Form, Depends, Request, HTTPException, status
from sqlalchemy.orm          import Session
from schemas.login import LoginRequest
from utils.generate_uuid     import generate_uuid
from datetime                import datetime

from models.association      import user_group
from models.tenant           import Tenant
from models.user            import User
from models.ip_address       import IPAddress
from database.session        import get_db
from utils.security          import authenticate_account, create_access_token

router = APIRouter()
from fastapi import APIRouter, Form, Depends, Request, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from utils.generate_uuid import generate_uuid
from datetime import datetime
from database.session import get_db
from utils.security import authenticate_account, create_access_token

router = APIRouter()

@router.post("/login")
async def login(
    request: Request,
    user: LoginRequest,
    db: Session = Depends(get_db)
):
    try:
        # Authenticate account (Tenant or User)
        account = authenticate_account(user.email, user.password, db)
        client_ip = request.client.host

        # Determine role and related IDs
        ip_id = generate_uuid()
        tenant_id = None
        user_id = None
        if isinstance(account, Tenant):
            tenant_id = account.id
            role = "tenant"
        elif isinstance(account, User):
            user_id = account.id
            role = account.role
        else:
            raise HTTPException(status_code=400, detail="Unknown account type")

        # Log IP via stored procedure
        try:
            db.execute(
                text(
                    "CALL sp_insert_ip_address(:id, :ip_address, :email, :tenant_id, :user_id);"
                ),
                {
                    "id": ip_id,
                    "ip_address": client_ip,
                    "email": account.email,
                    "tenant_id": tenant_id,
                    "user_id": user_id
                }
            )
            db.commit()
        except Exception as e:
            db.rollback()
            # Logging failure should not block login
            print(f"Failed to log IP address: {e}")

        # Create JWT access token
        jti = generate_uuid()
        access_token = create_access_token({
            "email": user.email,
            "role": role,
            "id": str(account.id),
            "jti": jti,
            "ip": client_ip
        })

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": role
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )