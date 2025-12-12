import os
from database.db_operation import get_engine
from fastapi import Depends, HTTPException, Path, Request, status
import re
from sqlalchemy import text
from .generate_uuid import generate_uuid

MASTER_DB = os.getenv('MASTER_DB', 'postgres')

def validate_db_name(name: str):
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$', name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid database name format. Use letters, numbers, and underscores."
        )
    return name

def validate_table_name(name: str):
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$', name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table name format. Use letters, numbers, and underscores."
        )
    return name

def create_database_if_not_exists(db_name: str):
    master_conn = get_engine(MASTER_DB).execution_options(
        isolation_level="AUTOCOMMIT"
    ).connect()

    try:
        # Check if the database already exists
        result = master_conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name}
        ).scalar()

        if result:
            print(f"Created Public Database '{db_name}'")
        else:
            master_conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"Created Public Database '{db_name}'")
    finally:
        master_conn.close()

# --------------------
def validate_db_name(name: str) -> str:
    
    if not name or name.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database name cannot be empty"
        )
    
    # Check name length
    if len(name) > 63:  # PostgreSQL limitation
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database name must be 63 characters or less"
        )
    
    # Check that name contains only allowed characters
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database name can only contain letters, numbers, and underscores"
        )
        
    # Check that name doesn't start with a number (PostgreSQL limitation)
    if re.match(r'^[0-9]', name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database name cannot start with a number"
        )
    
    # Check for reserved keywords
    reserved_keywords = ['pg_', 'postgres', 'template']
    if any(name.lower().startswith(kw) for kw in reserved_keywords):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database name cannot start with reserved prefixes: {', '.join(reserved_keywords)}"
        )
    
    return name

def sanitize_name(raw: str) -> str:
    
    name = raw.lower()
    
    name = re.sub(r'[^a-z0-9\-_.]', '-', name)
    
    name = re.sub(r'[-\.]{2,}', '-', name)
    
    name = name.strip('-._')
    
    if len(name) > 63:
        name = name[:63].rstrip('-.')
    
    if len(name) < 3:
        name += generate_uuid().hex[: (3 - len(name))]
    
    if name.startswith('goog'):
        name = 'b-' + name
    
    if re.fullmatch(r'\d+(\.\d+){3}', name):
        name = 'b-' + name
    return name

