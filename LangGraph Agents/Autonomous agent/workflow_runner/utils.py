# File Name: utils.py
# Purpose: Store helper functions like extract_runnable_node_list, group_by_source_and_function, etc.

# ________________________________________

# Helping Functions

# all nodes output registory
all_node_outputs = {
    'Ask_AI': 'ai_response',
    'Website_Scraper':'website_scraped_content',
    # 'Blog_Writer' : 'blog',
    'Get_Youtube_Transcript': 'transcript',
    'summarize': 'summary'
}



def group_by_source_and_function(dicts):
    grouped = {}
    for item in dicts:
        key = (item['source'], item['function'])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(item)
    return grouped


def check_previous_node(node_id,node_list):
    target = node_id
    previous_element = ''
    if target in node_list:
        index = node_list.index(target)  # Get the index of the target element
        if index > 0:  # Check if there is a previous element
            previous_element = node_list[index - 1]
            print(f"The previous element of '{target}' is '{previous_element}'.")
        else:
            print(f"'{target}' has no previous element.")
    else:
        print(f"'{target}' is not in the list.")
    return previous_element



def extract_nodes(input_json):
  flow = []
  edges = input_json['edges']
  current_node = '__start__'
  while current_node != '__end__':
      flow.append(current_node)
      # Find the next node in the flow:
      next_edge = next(edge for edge in edges if edge['source'] == current_node)
      current_node = next_edge['target']
  flow.append('__end__')
  return flow






