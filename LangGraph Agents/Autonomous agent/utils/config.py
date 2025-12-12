import re
from dotenv     import load_dotenv
import os
import pathlib
import sys

load_dotenv()

# Project root for imports
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Secret and algorithm
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM   = os.getenv("ALGORITHM")
ALGORITHM_JWT   = os.getenv("ALGORITHM_JWT")
ACCESS_TOKEN_EXPIRE_MINUTES = 3600

# Email credentials
SMTP_SERVER   = os.getenv("SMTP_SERVER")
SMTP_PORT     = os.getenv("SMTP_PORT")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD= os.getenv("EMAIL_PASSWORD")

# Database credentials (for dynamic engines)
DB_USER       = os.getenv('DB_USER')
DB_PASSWORD   = os.getenv('DB_PASSWORD')
DB_HOST       = os.getenv('DB_HOST', 'localhost')
DB_PORT       = os.getenv('DB_PORT', 5432)


# Bucket Credentials
_GS_URI_RE    = re.compile(r"^gs://([^/]+)/?$")
project       = os.getenv("PROJECT_ID")

# db agent 
DG_AGENT_JSON_PATH = os.getenv("DG_AGENT_JSON_PATH")

# Public Workflow Execution
PUBLIC_JWT_SECRET: str = os.getenv("PUBLIC_JWT_SECRET")
PUBLIC_JWT_ALGORITHM: str = os.getenv("PUBLIC_JWT_ALGORITHM")
PUBLIC_JWT_EXPIRES_IN: int = 3600

DATABASE_URL: str = os.getenv("DATABASE_URL")
JWT_PRIVATE_KEY_PATH: str = os.getenv("JWT_PRIVATE_KEY_PATH")
JWT_PUBLIC_KEY_PATH: str = os.getenv("JWT_PUBLIC_KEY_PATH")
JWT_ISSUER: str = os.getenv("JWT_ISSUER", "workflow-api")
REDIS_URL: str = os.getenv("REDIS_URL")