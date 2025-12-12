from typing import List

def split_text(input_text: str, delimiter: str = None, split_on_newline: bool = False) -> List[str]:
    if split_on_newline:
        # Split the text by line breaks if split_on_newline is True
        return input_text.splitlines()
    elif delimiter is not None:
        # Split the text by the specified delimiter if it's provided
        return input_text.split(delimiter)
    else:
        # If delimiter is None and split_on_newline is False, return the text as is
        return [input_text]

# Example usage:

# Split by comma (user-specified delimiter)
input_text1 = "apple,banana,orange"
delimiter1 = ","
result1 = split_text(input_text1, delimiter1)
print(result1)  # Output: ['apple', 'banana', 'orange']

# Split by exclamation mark (user-specified delimiter)
input_text2 = "hello!world!how!are!you"
delimiter2 = "!"
result2 = split_text(input_text2, delimiter2)
print(result2)  # Output: ['hello', 'world', 'how', 'are', 'you']

# Split by line breaks (split_on_newline=True)
input_text3 = "First line\nSecond line\nThird line"
result3 = split_text(input_text3, split_on_newline=True)
print(result3)  # Output: ['First line', 'Second line', 'Third line']

# Split by space (user-specified delimiter)
input_text4 = "#happy #coding #automation"
delimiter4 = " "
result4 = split_text(input_text4, delimiter4)
print(result4)  # Output: ['#happy', '#coding', '#automation']

# If no delimiter and no split_on_newline, return the text as a single element list
input_text5 = "No delimiter, just a plain string."
result5 = split_text(input_text5)
print(result5)  # Output: ['No delimiter, just a plain string.']