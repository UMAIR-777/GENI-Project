"""
Create List
FR: ListOperations-FR-2
desc: Creates a list from two items.
core use-cases: Initializing small datasets.
important edge-cases: None or invalid inputs.
"""

def create_list(item1, item2):
    """
    Creates a list containing two items in the given order.
    
    Args:
        item1: The first item to include.
        item2: The second item to include.
    
    Returns:
        list: A list with item1 and item2.
    """
    return [item1, item2]