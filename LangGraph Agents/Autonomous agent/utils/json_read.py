import json
import os


def read_json_file(filepath):

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    if not filepath.endswith('.json'):
        raise ValueError("Provided file is not a JSON file.")

    if os.path.getsize(filepath) == 0:
        raise ValueError("File is empty.")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON content: {e}")
    except PermissionError:
        raise PermissionError("Permission denied while reading the file.")
    except Exception as e:
        raise Exception(f"Unexpected error occurred: {e}")