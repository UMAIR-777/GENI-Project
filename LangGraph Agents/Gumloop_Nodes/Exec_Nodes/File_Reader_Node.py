from pathlib import Path
from typing import Union

def file_reader(file_name: str) -> str:
    """
    Reads the content of a text file.

    Args:
        file_name (str): Path to the file to read.

    Returns:
        str: Content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If the file cannot be read.
    """
    file_path = Path(file_name)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_name}")
    if not file_path.is_file():
        raise IOError(f"Path is not a file: {file_name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        raise IOError(f"Failed to read file: {str(e)}")
    

# file = r'Azaan.txt'
# print(file_reader(file))