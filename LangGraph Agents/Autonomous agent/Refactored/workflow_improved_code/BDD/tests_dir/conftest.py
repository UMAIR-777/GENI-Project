from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env file from src directory relative to project root
env_path = Path(__file__).resolve().parent.parent.parent / "src" / ".env"
load_dotenv(dotenv_path=env_path)

# Optionally print to confirm loading
print(f"Loaded environment variables from {env_path}")
