from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Float, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.base import Base
from utils.generate_uuid import generate_uuid
from pgvector.sqlalchemy import Vector


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    is_public = Column(Boolean, default=False)
    version = Column(Integer, nullable=False, default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)    
    tenant_id = Column(String, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(String, ForeignKey('group.id', ondelete='CASCADE'), nullable=True)
    embedding = Column(Vector(1024), nullable=True)  # For vector search


    tenant = relationship("Tenant", back_populates="workflows")
    group = relationship("Group", back_populates="workflows")
    
   

   
