# app/models.py

from sqlalchemy import Column, ForeignKey, String, Text, JSON, DateTime, func
from sqlalchemy.orm import relationship
from database.base import Base

class CUJ(Base):
    __tablename__ = "cuj"

    # Use a string PK since we're generating a UUID
    id = Column(String, primary_key=True, index=True)

    # tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    # tenant = relationship("Tenant", back_populates="cuj")

    # store the raw JSON inputs/outputs
    strategy_input        = Column(JSON, nullable=False)
    project_metadata      = Column(JSON, nullable=True)
    analysis              = Column(JSON, nullable=True)
    competitor_analysis   = Column(JSON, nullable=True)
    segmentation          = Column(JSON, nullable=True)
    market_fit            = Column(JSON, nullable=True)
    cuj_data              = Column(JSON, nullable=True)

    # free-form text fields
    bdd_feature           = Column(Text, nullable=True)
    architecture_feature  = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
