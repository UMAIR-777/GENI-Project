from typing import List

def chunk_text(text: str, chunk_size: int) -> List[str]:
    # List comprehension to create the chunks
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# Example usage:

# Text to chunk
input_text = "This is a long text that needs to be divided into chunks based on a specified size."
chunk_size = 15

# Get the chunks
result = chunk_text(input_text, chunk_size)
print(result)