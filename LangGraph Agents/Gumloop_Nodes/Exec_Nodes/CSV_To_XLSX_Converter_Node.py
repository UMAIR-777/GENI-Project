import pandas as pd
from pathlib import Path

def csv_to_xlsx_converter(csv_file_name: str, xlsx_file_name: str) -> str:
    """
    Converts a CSV file to an XLSX file.

    Args:
        csv_file_name (str): Path to the input CSV file.
        xlsx_file_name (str): Path to the output XLSX file.

    Returns:
        str: Path to the generated XLSX file.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the CSV file is malformed.
    """
    csv_path = Path(csv_file_name)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_name}")
    
    try:
        df = pd.read_csv(csv_path)
        df.to_excel(xlsx_file_name, index=False)
        return xlsx_file_name
    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty or malformed")