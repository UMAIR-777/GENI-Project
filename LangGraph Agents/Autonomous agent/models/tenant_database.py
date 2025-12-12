from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from database.base import Base
from utils.generate_uuid import generate_uuid

class TenantDatabase(Base):
    __tablename__ = 'tenant_databases'
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String)
    schema_name = Column(String, unique=True)
    tenant_id = Column(String, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_tenant_db'),
    )