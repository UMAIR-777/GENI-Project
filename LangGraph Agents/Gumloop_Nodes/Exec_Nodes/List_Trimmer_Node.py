"""
List Trimmer
FR: ListOperations-FR-6
desc: Trims a list to a specified number of items or range.
core use-cases: Limiting data size.
important edge-cases: Invalid indices, list shorter than requested.
"""

def list_trimmer(lst, items_to_keep=None, start_index=None, end_index=None):
    """
    Trims a list to keep a specified number of items or range.
    
    Args:
        lst (list): The list to trim.
        items_to_keep (int): Number of items to keep. Defaults to None.
        start_index (int): Start index to keep from. Defaults to None.
        end_index (int): End index to keep until. Defaults to None.
    
    Returns:
        list: The trimmed list.
    
    Raises:
        TypeError: If the input is not a list.
        ValueError: If both items_to_keep and range are specified.
    """
    if not isinstance(lst, list):
        raise TypeError("Input must be a list.")
    if items_to_keep is not None and (start_index is not None or end_index is not None):
        raise ValueError("Cannot specify both items_to_keep and range.")
    if items_to_keep is not None:
        return lst[:items_to_keep]
    if start_index is not None and end_index is not None:
        return lst[start_index:end_index]
    return lst

# input_list = ['A', 'B', 'C', 'D', 'E']
# keep = 3
# print(list_trimmer(input_list,start_index=1,end_index=4))