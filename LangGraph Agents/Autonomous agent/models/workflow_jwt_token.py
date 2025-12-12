import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, text
from database.base import Base
from utils.generate_uuid    import generate_uuid

class JWTToken(Base):
    __tablename__ = "jwt_tokens"

    id              = Column(String, primary_key=True, default=generate_uuid, index=True)
    # tenant_id       = Column(String, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    workflow_id = Column(String, unique=True, nullable=False)
    jti = Column(String(36), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
