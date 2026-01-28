# db/models.py
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

# ----------------------------
# Leads Table
# ----------------------------
class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    interest = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ----------------------------
# Workflows Table
# ----------------------------
class Workflow(Base):
    __tablename__ = "workflows"

    call_sid = Column(String, primary_key=True)   # Twilio identity
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    state = Column(JSON, nullable=False)
    current_node = Column(String)
    waiting_for = Column(String)
    is_paused = Column(Boolean, default=False)
    resume_at = Column(DateTime)
    status = Column(String, default="running")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


