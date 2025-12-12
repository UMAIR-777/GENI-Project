import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Get the project root directory
project_root = Path(__file__).parent
src_path = project_root / "src"

# Load environment variables from .env file in src directory
dotenv_path_src = os.path.join(project_root, 'src', '.env')
load_dotenv(dotenv_path_src)

# Load environment variables from .env file in BDD/tests_dir/test directory
dotenv_path_test = os.path.join(project_root, 'BDD', 'tests_dir', 'test', '.env')
load_dotenv(dotenv_path_test)

# Add both project root and src directory to Python path
sys.path.append(str(project_root))
sys.path.append(str(src_path))
