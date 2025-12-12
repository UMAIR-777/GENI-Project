from sqlalchemy import Column, String, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database.base import Base
from pgvector.sqlalchemy import Vector
from utils.generate_uuid import generate_uuid



class Node(Base):
    __tablename__ = "nodes"
    id               =  Column(String,  primary_key=True, default=generate_uuid, index=True)
    code = Column(String, nullable=False)  # Add this line
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    name = Column(String, nullable=False, unique=True)
    input = Column(String, nullable=False)
    output = Column(String, nullable=False)
    tags = Column(String, nullable=False)
    description = Column(String, nullable=False)
    spo = Column(JSONB, nullable=False)  # Changed from pg8000.JSONB to sqlalchemy.dialects.postgresql.JSONB
    node_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    uri = Column(String, nullable=True)


