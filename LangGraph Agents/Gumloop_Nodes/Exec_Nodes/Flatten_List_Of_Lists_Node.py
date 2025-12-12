"""
Flatten List of Lists
FR: ListOperations-FR-4
desc: Flattens a nested list into a single-level list.
core use-cases: Simplifying data structures.
important edge-cases: Deeply nested lists.
"""

def flatten_list(nested_list):
    """
    Flattens a nested list into a single-level list.
    
    Args:
        nested_list (list): The nested list to flatten.
    
    Returns:
        list: A flattened version of the nested list.
    
    Raises:
        TypeError: If the input is not a list.
    """
    if not isinstance(nested_list, list):
        raise TypeError("Input must be a list.")
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result