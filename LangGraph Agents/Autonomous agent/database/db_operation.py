import importlib
import os
import pkgutil
from sqlalchemy.orm import configure_mappers
from sqlalchemy import create_engine, text
from .base import Base, engine
from .procedure_loader import load_all_procedures
from .session import get_db
import models

conn = get_db()

MASTER_DB = os.getenv('MASTER_DB', 'postgres')

def ensure_vector_extension():
    try:
        with engine.connect() as conn:
            # conn.execute(text("CREATE EXTENSION IF NOT EXISTS hnsw;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()  # Explicit commit to ensure extension is created
            print("✅ 'hnsw' extension is ensured in the database.")
            print("✅ 'vector' extension is ensured in the database.")
    except Exception as e:
        print(f"❌ Failed to ensure 'vector' extension: {e}")
        raise  # Re-raise exception to prevent further execution

def get_engine(database: str):
    user = os.getenv('DB_USER')
    pwd = os.getenv('DB_PASSWORD')
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', 5432)
    url = f"postgresql://{user}:{pwd}@{host}:{port}/{database}"
    return create_engine(url)

def create_database_if_not_exists(db_name: str):
    master_engine = get_engine(MASTER_DB)
    with master_engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name}
        ).scalar()
        if not result:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"Created Public Database '{db_name}'")

def db_operation():
    # Import all models to ensure they're registered with Base
    for _, name, _ in pkgutil.iter_modules(models.__path__):
        importlib.import_module(f"models.{name}")
    
    # Configure mappers after all models are imported
    configure_mappers()

    # Interactive prompt for development environment
    answer = input("🔄 Do you want to DELETE and RECREATE the database schema? (y/N): ").strip().lower()
    
    if answer == "y":
        print("⚠️ Dropping all tables...")
        try:
            with engine.begin() as conn:
                for table in reversed(Base.metadata.sorted_tables):
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table.name}" CASCADE'))
            print("✅ All tables dropped.")
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            return

    # Ensure vector extension is enabled before creating tables
    ensure_vector_extension()

    # Create all tables
    print("🔧 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created")

    # Load stored procedures
    print("📥 Loading stored procedures...")
    load_all_procedures()
    print("✅ Procedures loaded")