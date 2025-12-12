"""
Duplicate List
FR: ListOperations-FR-7
desc: Creates a list of duplicates based on size or reference.
core use-cases: Generating placeholder data.
important edge-cases: Zero or negative size, empty reference.
"""

def duplicate(value, list_size=None, reference=None):
    """
    Creates a list of duplicates based on size or reference list.
    
    Args:
        value: The value to duplicate.
        list_size (int): The desired size of the output list. Defaults to None.
        reference (list): Reference list to match size. Defaults to None.
    
    Returns:
        list: A list of the value repeated to match the specified size or reference.
    
    Raises:
        ValueError: If neither list_size nor reference is provided.
    """
    if list_size is not None and not isinstance(list_size, int) or list_size < 0:
        raise ValueError("list_size must be a non-negative integer.")
    if reference is not None and not isinstance(reference, list):
        raise ValueError("reference must be a list.")
    if list_size is not None:
        return [value] * list_size
    if reference is not None:
        return [value] * len(reference)
    raise ValueError("Either list_size or reference must be provided.")

#Test 1:
# Input: "Pending"
# Size: 5
# Result: ["Pending", "Pending", "Pending", "Pending", "Pending"]

#Test 2:
# Input: "Unknown"
# Reference: [1, 2, 3]
# Result: ["Unknown", "Unknown", "Unknown"]

#Test 3:
# Input: "{{placeholder}}"
# Size: 3
# Result: ["{{placeholder}}", "{{placeholder}}", "{{placeholder}}"]

#Results of Test 1:
# val = "Pending"
# size = 5
# print(duplicate(val,list_size=size))
# Output => ['Pending', 'Pending', 'Pending', 'Pending', 'Pending']

#Results of Test 2:
# val = "Unknown"
# ref = [1, 2, 3]
# print(duplicate(val,3,reference=ref))
# Output => ['Unknown', 'Unknown', 'Unknown']

#Results of Test 3:
# val = "{{placeholder}}"
# size = 3
# print(duplicate(val,list_size=size))
# Output => ['{{placeholder}}', '{{placeholder}}', '{{placeholder}}']