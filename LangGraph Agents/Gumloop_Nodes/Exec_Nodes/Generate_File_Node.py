from pathlib import Path

def generate_file(file_name: str, file_type: str, content: str = "") -> str:
    """
    Generates a new file with the specified name and type.

    Args:
        file_name (str): Name of the file to create.
        file_type (str): Type of the file (e.g., 'txt', 'csv').
        content (str): Optional content to write to the file.

    Returns:
        str: Path to the generated file.

    Raises:
        ValueError: If the file type is invalid.
        IOError: If the file cannot be created.
    """
    if not file_type:
        raise ValueError("File type must be specified")
    
    file_path = Path(f"{file_name}.{file_type}")
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return str(file_path)
    except Exception as e:
        raise IOError(f"Failed to generate file: {str(e)}")