
# "File Name": "graph_configs.json",
# "Purpose": "Store JSON configurations for different workflows (e.g., self_Rag_Agent, YouTube Transcript Summarizer, etc.)."

# ------------------------------------------------------------------------
json_app_1 = {
  'main':{
'state':{'mainstate' : 'q1_state', 'inputstate' : None, 'outputstate' : 'output_q1_state'},
'nodes': [
 
  {'id': 'response_1',
   'type': 'runnable',
   'data': {'id': ['langgraph', 'utils', 'runnable', 'RunnableCallable'], 'name': 'response_1'},
   'inputs': {'question': "Who is Ali"},
   'output': {'ans_1': ''}},
  
  {'id': '__start__', 'type': 'schema', 'data': '__start__'},

  {'id': '__end__', 'type': 'schema', 'data': '__end__'}],

 'edges': [{'source': '__start__', 'target': 'response_1'},
  {'source': 'response_1', 'target': '__end__'}]}
}
# -----------------------------------------------------------------------------
# sample app json with subgraphs

main_app_json={

'main':{
  'state':{'mainstate' : 'finalState', 'inputstate' : None, 'outputstate' : None},

  'nodes': [
      
  {'id': 'response1',
   'type': 'runnable',
   'data': {'id': ['langgraph', 'graph', 'state', 'CompiledStateGraph'],'name': 'response1'},
   'inputs': {'question': "Who is Ali"},
   'output': {'ans_1': ''}},

  {'id': 'response2',
   'type': 'runnable',
   'data': {'id': ['langgraph', 'graph', 'state', 'CompiledStateGraph'],'name': 'response2'},
   'inputs': {'question': "Who is Ali"},
   'output': {'ans_2': ''}},

  {'id': 'model',
   'type': 'runnable',
   'data': {'id': ['langgraph', 'utils', 'runnable', 'RunnableCallable'],'name': 'model'},
   'inputs': {'question': "Who is Ali"},
   'output': {'final_ans': ''}},

  {'id': '__start__', 'type': 'schema', 'data': '__start__'},
  {'id': '__end__', 'type': 'schema', 'data': '__end__'}],

 'edges': 
 [{'source': '__start__', 'target': 'response1'},
  {'source': '__start__', 'target': 'response2'},
  {'source': 'model', 'target': '__end__'},
  {'source': 'response1', 'target': 'model'},
  {'source': 'response2', 'target': 'model'}]},


'response1' : {
'state':{'mainstate' : 'q1_state', 'inputstate' : None, 'outputstate' : 'output_q1_state'},
'nodes': [
 
  {'id': 'response_1',
   'type': 'runnable',
   'data': {'id': ['langgraph', 'utils', 'runnable', 'RunnableCallable'], 'name': 'response_1'},
   'inputs': {'question': "Who is Ali"},
   'output': {'ans_1': ''}},
  
  {'id': '__start__', 'type': 'schema', 'data': '__start__'},

  {'id': '__end__', 'type': 'schema', 'data': '__end__'}],

 'edges': [{'source': '__start__', 'target': 'response_1'},
  {'source': 'response_1', 'target': '__end__'}]},


'response2' : {
 'state':{'mainstate' : 'q2_state', 'inputstate' : None, 'outputstate' : 'output_q2_state'},

 'nodes': [
  {'id': 'response_2',
   'type': 'runnable',
   'data': {'id': ['langgraph', 'utils', 'runnable', 'RunnableCallable'],'name': 'response_2'},
   'inputs': {'question': "Who is Ali"},
   'output': {'ans_2': ''}},

  {'id': '__start__', 'type': 'schema', 'data': '__start__'},

  {'id': '__end__', 'type': 'schema', 'data': '__end__'}],
 
 'edges': [
  {'source': '__start__', 'target': 'response_2'},
  {'source': 'response_2', 'target': '__end__'}]}
}
