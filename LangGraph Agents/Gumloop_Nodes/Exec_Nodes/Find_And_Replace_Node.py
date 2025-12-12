def find_and_replace(input_text, replacements):
    output_text = input_text
    for replacement in replacements:
        find_word = replacement.get('Find word')
        replace_word = replacement.get('Replace with')
        
        # Perform the replacement operation
        if find_word and replace_word:
            output_text = output_text.replace(find_word, replace_word)
    
    return output_text

# Example usage:
replacements = [
    {'Find word': 'apple', 'Replace with': 'orange'},
    {'Find word': 'quick', 'Replace with': 'fast'}
]

input_text = "The quick brown fox jumped over the apple tree."
output_text = find_and_replace(input_text, replacements)
print(output_text)