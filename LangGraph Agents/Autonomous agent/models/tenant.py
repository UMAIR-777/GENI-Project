from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from database.base import Base
from utils.generate_uuid import generate_uuid
from models.user import User
from models.group import Group
from models.workflow import Workflow
from models.ip_address import IPAddress
from models.bucket import Bucket


class Tenant(Base):
    __tablename__ = "tenants"

    id                   = Column(String,  primary_key=True, default=generate_uuid, index=True)

    name                 = Column(String,  unique=True,   nullable=False)
    email                = Column(String,  unique=True,   nullable=False)
    hashed_password      = Column(String,  nullable=True)
    tenant_nodes_bucket  = Column(String,  unique=True,   nullable=False)
    tenant_database_name = Column(String,  unique=False,   nullable=False)
    role                 = Column(String,  default="tenant", nullable=False)

    user                 = relationship("User",      back_populates="tenant",    cascade="all, delete-orphan")
    group                = relationship("Group",     back_populates="tenant",    cascade="all, delete-orphan")
    workflows            = relationship("Workflow",  back_populates="tenant",    cascade="all, delete-orphan")
    ip_addresses         = relationship("IPAddress", back_populates="tenant",   cascade="all, delete-orphan")
    buckets              = relationship("Bucket", back_populates="tenant",cascade="all, delete-orphan",passive_deletes=True)
    
    
