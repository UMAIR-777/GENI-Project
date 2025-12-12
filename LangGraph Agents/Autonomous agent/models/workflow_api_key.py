import uuid
from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from database.base import Base
from utils.generate_uuid    import generate_uuid
class APIKeyStatus(PyEnum):
    ACTIVE = "active"
    REVOKED = "revoked"

class APIKey(Base):
    __tablename__ = "api_keys"

    id              = Column(String, primary_key=True, default=generate_uuid, index=True)
    tenant_id       = Column(String, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    workflow_id = Column(String, unique=True, nullable=False)
    key_hash = Column(String(60), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status = Column(Enum(APIKeyStatus), default=APIKeyStatus.ACTIVE, nullable=False)
    description = Column(String(255), nullable=True)
