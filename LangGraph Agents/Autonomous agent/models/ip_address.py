from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.base import Base
from utils.generate_uuid import generate_uuid


class IPAddress(Base):
    __tablename__   =  "ip_addresses"

    id               = Column(String,  primary_key=True, default=generate_uuid, index=True)

    ip_address       = Column(String,  nullable=False)
    email            = Column(String,  nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tenant_id        = Column(String,  ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    user_id          = Column(String,  ForeignKey('user.id', ondelete='CASCADE'),   nullable=True)

    tenant           = relationship("Tenant",        back_populates="ip_addresses")
    user             = relationship("User",          back_populates="ip_addresses")
