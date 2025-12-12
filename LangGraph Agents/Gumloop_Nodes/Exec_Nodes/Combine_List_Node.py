"""
Combine Lists
FR: ListOperations-FR-1
desc: Combines two lists into one, preserving order.
core use-cases: Merging user lists, appending data.
important edge-cases: Empty lists, non-list inputs.
"""

def combine_lists(list1, list2):
    """
    Combines two lists into one, preserving the order of elements.
    
    Args:
        list1 (list): The first list to combine.
        list2 (list): The second list to combine.
    
    Returns:
        list: A new list containing all elements from both lists in order.
    
    Raises:
        TypeError: If either input is not iterable.
    """
    if not isinstance(list1, list) or not isinstance(list2, list):
        raise TypeError("Both inputs must be lists.")
    return list1 + list2