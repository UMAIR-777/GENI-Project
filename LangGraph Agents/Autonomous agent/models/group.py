from sqlalchemy             import Column, String, ForeignKey
from sqlalchemy.orm         import relationship
from database.base          import Base
from utils.generate_uuid    import generate_uuid

class Group(Base):
    __tablename__ = "group"

    id              = Column(String, primary_key=True, default=generate_uuid, index=True)
    name            = Column(String, nullable=False)
    tenant_id       = Column(String, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)

    tenant          = relationship("Tenant", back_populates="group")
    user            = relationship("User", secondary="user_group", back_populates="group")
    
    workflows       = relationship(
        "Workflow", back_populates="group", cascade="all, delete-orphan"
    )