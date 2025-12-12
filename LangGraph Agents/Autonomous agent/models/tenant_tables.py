from sqlalchemy import Column, Integer, String, ForeignKey
from database.base import Base
from utils.generate_uuid import generate_uuid

class TenantTable(Base):
    __tablename__ = 'tenant_tables'
    id              = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String)
    database_name = Column(String)
    tenant_id       = Column(String, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    schema_definition = Column(String)  # JSON string
