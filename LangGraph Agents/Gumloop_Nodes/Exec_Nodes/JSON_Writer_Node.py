import json

def json_writer(keys, **kwargs):
    """
    Creates or updates a JSON object using the provided keys and their corresponding values.

    Args:
        keys (str): A comma-separated string of keys to be added or updated in the JSON object.
        kwargs: Key-value pairs representing the values to assign to the keys.

    Returns:
        str: A stringified JSON object after adding/updating the keys and values.
    """
    try:
        # Initialize an empty dictionary to hold the JSON object
        json_data = {}
        # Split the keys string into a list of individual keys
        keys_list = keys.split(",")
        # Update the JSON object with the provided key-value pairs
        for key in keys_list:
            if key in kwargs:
                json_data[key] = kwargs[key]
        # Convert the dictionary to a JSON string
        return json.dumps(json_data)
    except Exception as e:
        raise ValueError(f"Error creating/updating JSON: {e}")
