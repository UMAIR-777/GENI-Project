from datetime                               import datetime, timedelta
from fastapi                                import APIRouter, Depends, HTTPException, status
from sqlalchemy                             import text
from sqlalchemy.orm                         import Session

from fastapi.security                       import HTTPAuthorizationCredentials
from database.session                       import get_db
from dependencies.dependency_injections     import get_current_tenant, security
from schemas.login                          import UserOut, ValidateTokenResponse
from schemas.tenant                         import TenantCreate
from utils.security                         import get_password_hash
from utils.email_sender                     import send_otp_email
from utils.otp                              import generate_otp
from error_handlers.exceptions.http         import ConflictError, BadRequestError
from error_handlers.exceptions.database     import DatabaseError
from utils.generate_uuid                    import generate_uuid
import json

router = APIRouter()

@router.post(
    "/register",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register a new tenant (sends OTP)"
)
async def register_tenant(
        tenant_data: TenantCreate,
        db: Session = Depends(get_db),
):
    # ─── Check for existing email or name via SP ─────────────────────────────
    existing = db.execute(
        text("SELECT fn_check_tenant_exists(:email, :name)"),
        {"email": tenant_data.email, "name": tenant_data.name}
    ).scalar()
    if existing:
        raise ConflictError("Email or tenant name already registered")

    # ─── Generate and persist OTP record via SP ──────────────────────────────
    otp_code = generate_otp()
    print(otp_code)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    otp_id = generate_uuid()
    try:
        db.execute(
            text(
                "CALL sp_insert_otp_verification(:id, :email, :otp, :expires_at, :purpose, :data_json);"
            ),
            {
                "id": otp_id,
                "email": tenant_data.email,
                "otp": otp_code,
                "expires_at": expires_at,
                "purpose": "register",
                "data_json": json.dumps({
                    "tenant_name": tenant_data.name,
                    "email": tenant_data.email,
                    "admin_password_hash": get_password_hash(tenant_data.password),
                    "role": "tenant"
                })
            }
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Failed to save OTP record via stored procedure: {e}")

    # ─── Send OTP email ──────────────────────────────────────────────────────
    sent = send_otp_email(tenant_data.email, otp_code)
    if not sent:
        raise BadRequestError("Unable to deliver OTP email; please try again later")

    return {"message": "OTP has been sent to your email address"}

@router.post(
    "/validate-token",
    response_model=ValidateTokenResponse,
    status_code = status.HTTP_200_OK
)
def validate_token_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    token = credentials.credentials

    try:
        tenant = get_current_tenant(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            db,
        )

    except HTTPException as exc:
        raise exc
    
    user_out = UserOut(
        id=generate_uuid(),
        email=tenant.email,
        name=tenant.name
    )
    return ValidateTokenResponse(valid=True, user=user_out)