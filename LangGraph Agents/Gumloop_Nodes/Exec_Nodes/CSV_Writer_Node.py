import csv
from pathlib import Path
from typing import List, Dict, Literal

def csv_writer(csv_file_name: str, data: List[Dict[str, str]], mode: Literal['append', 'write'] = 'append') -> str:
    """
    Writes data to a CSV file.

    Args:
        csv_file_name (str): Path to the CSV file.
        data (List[Dict[str, str]]): Data to write, where each dictionary represents a row.
        mode (Literal['append', 'write']): Whether to append to or overwrite the file.

    Returns:
        str: Path to the written CSV file.

    Raises:
        ValueError: If the data is empty or inconsistent.
    """
    if not data:
        raise ValueError("No data provided to write")
    
    file_path = Path(csv_file_name)
    write_header = not file_path.exists() or mode == 'write'
    
    try:
        with open(file_path, mode='a' if mode == 'append' else 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=data[0].keys())
            if write_header:
                writer.writeheader()
            writer.writerows(data)
        return str(file_path)
    except Exception as e:
        raise IOError(f"Failed to write CSV file: {str(e)}")