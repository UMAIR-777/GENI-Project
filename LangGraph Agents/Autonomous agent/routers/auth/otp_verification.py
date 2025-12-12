import os
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import json

from models.tenant import Tenant
from models.otp_verification import OTPVerification
from schemas.auth import OTPVerificationRequest
from database.session import get_db
from utils.bucket_operation import create_bucket
from utils.generate_uuid import generate_uuid

router = APIRouter()

PUBLIC_DATABASE_NAME = os.getenv('PUBLIC_DATABASE_NAME', 'unicorn')

@router.post(
    "/verify-registration-otp",
    status_code=status.HTTP_201_CREATED,
)
async def verify_otp(
    request: OTPVerificationRequest,
    db: Session = Depends(get_db),
):
    try:
        # 1) Fetch OTP using stored function
        otp_result = db.execute(
            text("""
                SELECT * 
                FROM get_valid_otp(
                    :email, 
                    :purpose, 
                    :otp, 
                    :now
                )
            """),
            {
                "email": request.email,
                "purpose": request.purpose,
                "otp": request.otp,
                "now": datetime.utcnow()
            }
        ).fetchone()

        if not otp_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP."
            )

        # 2) Parse JSON data safely
        try:
            data = (
                json.loads(otp_result.data) 
                if isinstance(otp_result.data, str) 
                else otp_result.data
            )
            if "email" not in data or "tenant_name" not in data:
                raise ValueError("Missing required fields in OTP data.")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP data: {str(e)}"
            )

        # 3) Check tenant existence
        exists = db.execute(
            text("SELECT tenant_exists(:email)"),
            {"email": data["email"]}
        ).scalar()

        if exists:
            db.execute(
                text("CALL delete_otp(:otp_id)"),
                {"otp_id": otp_result.id}
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A tenant with that email already exists."
            )
        
        tenant_id = generate_uuid()
        tenant_nodes_bucket = create_bucket(tenant_id)
        
        # 4) Create tenant with corrected parameters
        try:
            db.execute(
                text("""
                    CALL create_tenant(
                        :id, 
                        :name, 
                        :email, 
                        :hashed_password, 
                        :tenant_nodes_bucket, 
                        :tenant_database_name, 
                        :role
                    )
                """),
                {
                    "id": tenant_id,
                    "name": data["tenant_name"],
                    "email": data["email"],
                    "hashed_password": data["admin_password_hash"],
                    "tenant_nodes_bucket": tenant_nodes_bucket,   
                    "tenant_database_name": PUBLIC_DATABASE_NAME,
                    "role": "tenant"
                }
            )
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate entry or invalid data."
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

        # 5) Cleanup OTP
        db.execute(
            text("CALL delete_otp(:otp_id)"),
            {"otp_id": otp_result.id}
        )
        db.commit()

        return {
            "message": "Registration successful",
            "tenant_id": tenant_id,
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )