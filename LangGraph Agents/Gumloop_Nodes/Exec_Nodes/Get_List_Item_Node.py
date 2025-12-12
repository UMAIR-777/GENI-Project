"""
Get List Item
FR: ListOperations-FR-3
desc: Retrieves an item from a list by its index.
core use-cases: Accessing specific data points.
important edge-cases: Invalid indices.
"""

def get_list_item(lst, index):
    """
    Retrieves an item from a list at the specified index.
    
    Args:
        lst (list): The list to retrieve the item from.
        index (int): The index of the item to retrieve.
    
    Returns:
        any: The item at the specified index.
    
    Raises:
        TypeError: If the input is not a list.
        IndexError: If the index is out of range.
    """
    if not isinstance(lst, list):
        raise TypeError("Input must be a list.")
    return lst[index]