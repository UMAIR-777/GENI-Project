import pandas as pd
from pathlib import Path

def sort_csv(csv_file_name: str, column_index: int, sorted_csv_file_name: str, has_headers: bool = True, reverse_sort: bool = False) -> str:
    """
    Sorts a CSV file by a specific column.

    Args:
        csv_file_name (str): Path to the input CSV file.
        column_index (int): Index of the column to sort by.
        sorted_csv_file_name (str): Path to the output sorted CSV file.
        has_headers (bool): Whether the CSV file has headers.
        reverse_sort (bool): Whether to sort in descending order.

    Returns:
        str: Path to the sorted CSV file.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the column index is invalid.
    """
    csv_path = Path(csv_file_name)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_name}")
    
    try:
        df = pd.read_csv(csv_path, header=0 if has_headers else None)
        if column_index >= len(df.columns):
            raise ValueError(f"Column index {column_index} is out of range")
        
        df.sort_values(by=df.columns[column_index], ascending=not reverse_sort, inplace=True)
        df.to_csv(sorted_csv_file_name, index=False)
        return sorted_csv_file_name
    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty or malformed")