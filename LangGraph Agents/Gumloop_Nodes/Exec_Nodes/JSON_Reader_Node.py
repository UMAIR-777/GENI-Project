import json

def json_reader(json_string, keys):
    """
    Extracts values from a JSON string for the specified keys.

    Args:
        json_string (str): A string representing the JSON data.
        keys (str): A comma-separated string of keys whose values will be extracted.

    Returns:
        dict: A dictionary where each key is mapped to its corresponding value in the JSON data.
    """
    try:
        # Parse the JSON string
        json_data = json.loads(json_string)
        # Split the keys string into a list of individual keys
        keys_list = keys.split(",")
        # Extract the values for the specified keys
        result = {key: json_data.get(key) for key in keys_list}
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {e}")
