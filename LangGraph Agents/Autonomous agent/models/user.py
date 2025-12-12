from sqlalchemy         import Column, String, Boolean, ForeignKey
from sqlalchemy.orm     import relationship
from database.base      import Base
from utils.generate_uuid              import generate_uuid
from .association       import user_group

class User(Base):
    __tablename__   =   "user"

    id              =   Column(String, primary_key=True, default=generate_uuid, index=True)
    name            =   Column(String, nullable=False)
    email           =   Column(String, unique=True, index=True, nullable=False)
    hashed_password =   Column(String, nullable=True)
    tenant_id       =   Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    role            =   Column(String, nullable=False)  # 'team_member' or 'client'
    is_active       =   Column(Boolean, default=True, nullable=False)

    tenant          =    relationship(
                                "Tenant", 
                                back_populates      =       "user"
                                )
    group          =    relationship(
                                "Group", 
                                secondary           =       user_group, 
                                back_populates      =       "user"
                                )
    ip_addresses    =    relationship(
                                "IPAddress", 
                                back_populates      =       "user", 
                                cascade             =       "all, delete-orphan"
                                )