import zipfile
from pathlib import Path
from typing import Dict, List

def zip_file_reader(zip_file_name: str) -> Dict[str, str]:
    """
    Reads a ZIP file and extracts the names and contents of all files.

    Args:
        zip_file_name (str): Path to the ZIP file.

    Returns:
        Dict[str, str]: Dictionary where keys are file names and values are file contents.

    Raises:
        FileNotFoundError: If the ZIP file does not exist.
        zipfile.BadZipFile: If the file is not a valid ZIP archive.
    """
    file_path = Path(zip_file_name)
    if not file_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_file_name}")
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            return {name: zip_ref.read(name).decode('utf-8') for name in zip_ref.namelist()}
    except zipfile.BadZipFile:
        raise zipfile.BadZipFile(f"Invalid ZIP file: {zip_file_name}")