from sqlalchemy import Column, String, DateTime
from database.base import Base
from utils.generate_uuid import generate_uuid


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id               = Column(String,  primary_key=True, default=generate_uuid, index=True)

    jti              = Column(String(36), nullable=False)
    email            = Column(String,     nullable=True)
    exp              = Column(DateTime,   nullable=False)
    account_id       = Column(String,     nullable=False)
    account_type     = Column(String(20), nullable=False)  # 'client', 'tenant', etc.
