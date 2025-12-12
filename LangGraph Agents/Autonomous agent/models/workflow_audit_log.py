import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from database.base import Base
from utils.generate_uuid    import generate_uuid

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id              = Column(String, primary_key=True, default=generate_uuid, index=True)
    tenant_id       = Column(String, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    workflow_id     = Column(String, unique=True, nullable=False)
    timestamp       = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    api_key_id      = Column(String, ForeignKey("api_keys.id"), nullable=True)
    jwt_jti         = Column(String(36), nullable=True)
    jwt_sub         = Column(String(255), nullable=True)
    client_ip       = Column(String(45), nullable=False)
    user_agent      = Column(String(512), nullable=True)
    request_payload = Column(JSON, nullable=False)
    response_payload = Column(JSON, nullable=False)
    status_code     = Column(String(3), nullable=False)
