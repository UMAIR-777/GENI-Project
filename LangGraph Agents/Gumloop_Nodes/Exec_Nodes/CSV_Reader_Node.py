import csv
from pathlib import Path
from typing import Dict, List

def csv_reader(csv_file_name: str) -> Dict[str, List[str]]:
    """
    Reads a CSV file and dynamically creates outputs for each column using headers as keys.

    Args:
        csv_file_name (str): Path to the CSV file.

    Returns:
        Dict[str, List[str]]: Dictionary where keys are column headers and values are lists of column data.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the CSV file is empty or malformed.
    """
    file_path = Path(csv_file_name)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                raise ValueError("CSV file has no headers or is empty")
            
            # Initialize dictionary with headers as keys
            data = {header: [] for header in reader.fieldnames}
            
            for row in reader:
                for header in reader.fieldnames:
                    data[header].append(row[header])
            
            return data
    except csv.Error as e:
        raise ValueError(f"Malformed CSV file: {str(e)}")