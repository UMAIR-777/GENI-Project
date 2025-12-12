import os
import re
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .base import SessionLocal

def load_all_procedures():
    """Load procedures with proper dollar-quote handling"""
    db = SessionLocal()
    try:
        sp_dir = os.path.join(os.path.dirname(__file__), '../stored_procedures')
        
        for root, _, files in os.walk(sp_dir):
            for file in files:
                if file.endswith('.sql'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Split on semicolons that are outside of dollar-quoted blocks
                        statements = []
                        current = ""
                        in_dollar = False
                        
                        for line in content.split('\n'):
                            if '$$' in line:
                                in_dollar = not in_dollar
                            current += line + '\n'
                            
                            if not in_dollar and ';' in line:
                                statements.append(current.strip())
                                current = ""
                        
                        if current.strip():
                            statements.append(current.strip())
                        
                        for stmt in statements:
                            if stmt:
                                try:
                                    db.execute(text(stmt))
                                    db.commit()
                                    print(f"✅ Loaded statement from {file}")
                                except SQLAlchemyError as e:
                                    db.rollback()
                                    print(f"❌ Failed in {file}: {str(e)}")
                                    print(f"Problematic statement:\n{stmt[:300]}...")  # Show first 300 chars
                                    raise
    finally:
        db.close()