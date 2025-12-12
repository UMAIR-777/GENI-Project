from database.base          import Base
from sqlalchemy.dialects.postgresql import JSONB  # Correct import for JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy import  Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from utils.generate_uuid import generate_uuid


class Bucket(Base):
    __tablename__ = "buckets"

    
    bucket_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    bucket_uri = Column(String, unique=True, nullable=False)
    
    tenant_id = Column(
        String,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant = relationship("Tenant", back_populates="buckets")
    
    
    __table_args__ = (
        UniqueConstraint('name', 'tenant_id', name='uq_bucket_name_tenant'),
    )