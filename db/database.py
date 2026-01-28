from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load .env variables if you have them
load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")       # default to postgres
DB_PASSWORD = os.getenv("DB_PASSWORD", "strongumair777")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ai_voice_bot")

# Create SQLAlchemy engine
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    echo=True,  # True for debugging SQL
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
