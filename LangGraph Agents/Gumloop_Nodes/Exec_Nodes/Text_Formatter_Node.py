def text_formatter(value, action, truncate_range=None):
    if action == "To Lowercase":
        return value.lower()
    elif action == "To Uppercase":
        return value.upper()
    elif action == "To Propercase":
        return value.title()
    elif action == "Trim Spaces":
        return value.strip()
    elif action == "Truncate":
        # Ensure the truncate_range is provided and is a valid list with two values (start:end)
        if truncate_range and isinstance(truncate_range, list) and len(truncate_range) == 2:
            start, end = truncate_range
            return value[start:end]
        else:
            return "Please provide a valid truncation range in the form [start:end]"
    else:
        return "Invalid action specified"

# Example usage:
formatted_text = text_formatter("Hello World! This is a test of truncation.", "Truncate", [6, 20])
print(formatted_text)