from sqlalchemy import Column, String, DateTime, JSON
from database.base import Base
from utils.generate_uuid import generate_uuid


class OTPVerification(Base):
    __tablename__    =  "otp_verifications"

    id               =  Column(String,  primary_key=True, default=generate_uuid, index=True)

    email            =  Column(String,  index=True, nullable=False)
    otp              =  Column(String,  nullable=False)
    expires_at       =  Column(DateTime, nullable=False)
    purpose          =  Column(String,  nullable=True)
    data             =  Column(JSON,    nullable=True)
