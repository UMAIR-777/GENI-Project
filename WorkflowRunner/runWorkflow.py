# File Name: run_workflow.py
# Purpose: Execute the compiled workflow with input data. 
# Here i will use the main graphBuilder funtion from jsonToLangGraph file.

# ___________________________________________

from jsonToLangGraph import graph_builder
from graphStates import *
from graphConfigs import *



app,input_dict,node_list = graph_builder(main_app_json)
print("Workflow Results :")
print(app.invoke(input_dict))

# app,input_dict,node_list = graph_builder(json_app_1)
# print(app.invoke(input_dict))
# print("Workflow Results :")



