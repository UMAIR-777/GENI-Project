"""
Join List Items
FR: ListOperations-FR-5
desc: Joins list items into a string with optional separators.
core use-cases: Creating formatted outputs.
important edge-cases: Non-string items, empty lists.
"""

def join_list_items(lst, separator=",", newline=False):
    """
    Joins items in a list into a string with optional separators and newlines.
    
    Args:
        lst (list): The list of items to join.
        separator (str): The separator between items. Defaults to ",".
        newline (bool): If True, each item is on a new line. Defaults to False.
    
    Returns:
        str: The joined string.
    
    Raises:
        TypeError: If the input is not a list.
    """
    if not isinstance(lst, list):
        raise TypeError("Input must be a list.")
    if newline:
        return "\n".join(map(str, lst))
    return separator.join(map(str, lst))

# l1 = ["Line 1", "Line 2", "Line 3"]
# print(join_list_items(l1,",",True))