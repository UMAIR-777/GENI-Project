from sqlalchemy import Table, Column, String, ForeignKey
from database.base import Base

# Association table for user and group
user_group = Table(
    'user_group',
    Base.metadata,
    Column('user_id', String, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    Column('group_id', String, ForeignKey('group.id', ondelete='CASCADE'), primary_key=True),
)