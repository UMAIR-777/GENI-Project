# File Name: json_to_langgraph.py
# Purpose: Main logic to convert JSON configurations into executable LangGraph workflows.
# graph builder


# _______________________________________________________
# file jsonToLangGraph.py

from utils import *
from inspect import isframe
from typing import Dict, TypedDict, Optional, Callable
from langgraph.graph import StateGraph, END, START
from registry import get_function_reference, get_class_reference
from graphConfigs import *

def build_graph_from_json(app_json: Dict) -> Callable:
   
    
    #* get the first element of dict (get first key of dict and get its json)
    first_json_key = list(app_json.keys())[0]
    current_app_json = app_json[first_json_key]

    input_var_dict={}
    conditional_edges=[]

    #* get the state from the json and check type of states availabel   
    state = current_app_json.get('state')
    print(state)
    print("_"*10)
    mainstate_ref = get_class_reference(state['mainstate']) if state['mainstate'] is not None or 'None' else None
    inputstate_ref = get_class_reference(state['inputstate']) if state['inputstate'] is not None or 'None' else None
    outputstate_ref = get_class_reference(state['outputstate']) if state['outputstate'] is not None or 'None' else None
    #* use get_class_reference to get the specific stateclass refrence
    # Step 1: Initialize the graph with config
    workflow = StateGraph(state_schema=mainstate_ref, input=inputstate_ref, output=outputstate_ref)

    # Step 2: Add all nodes to the workflow based on the output JSON
    for node in current_app_json["nodes"]:
        #* Check whether current node has graphstate or runable
        # if 'CompiledStateGraph' in node['data']['id']:  (means currnt node of current_app_json)
        #* if graphstate then get its respective json and call recursive build_graph_from_json 
        if isinstance(node["data"], dict) and "id" in node["data"] and 'CompiledStateGraph' in node["data"]['id']:
            # if node is CompiledStateGraph
            node_id = node["id"]
            sub_graph_json = app_json[node_id]
            sub_workflow,input_var_dict= build_graph_from_json({node_id:sub_graph_json})
            workflow.add_node(node_id, sub_workflow.compile())

            
        else:
            # if node is RunnableCallable
            node_id = node["id"]
            # Skip special start and end nodes in this step
            if node_id in ["__start__", "__end__"]:
                continue
            # Retrieve the function for this node
            function_name = node["data"].get("name")
            function_ref = get_function_reference(function_name)
            # Add the node with the associated function
            workflow.add_node(node_id, function_ref)
            # extract input variables from node-json
            input_var_dict.update(node["inputs"])



    # Step 3: Set the entry point if there's an edge from "__start__"
    for edge in current_app_json["edges"]:
        if not "conditional" in edge:
            if edge["source"] == "__start__":
                workflow.add_edge(edge["source"],edge["target"])
                # workflow.set_entry_point(edge["target"])
            
    # Step 4: Set the end point if there's an edge from "__end__"
    for edge in current_app_json["edges"]:
      if not "conditional" in edge:
        if edge["target"] == "__end__":
            workflow.add_edge(edge["source"],edge["target"])
            

    # Step 5: Add edges to the workflow
    for edge in current_app_json["edges"]:

        if "conditional" in edge:
            # Retrieve the conditional edges and append to seprate conditional lists
            conditional_edges.append(edge)
        else:
            source = edge["source"]
            target = edge["target"]
            # Add a normal edge if it's not conditional
            workflow.add_edge(source, target)

    if conditional_edges:
        all_conditional_edges= group_by_source_and_function(conditional_edges)

        for conditional_edge in all_conditional_edges:
            
            if all_conditional_edges[conditional_edge][0]['condition_type'] == 'dict':
                conditional_dict={}
                edge_source, edge_function = conditional_edge
                for edge in all_conditional_edges[conditional_edge]:
                    conditional_dict[edge['data']]=edge['target']

                function_ref = get_function_reference(edge_function)
                workflow.add_conditional_edges(edge_source, function_ref, conditional_dict)
            
            # here we have main args in conditional-edge-dict source, target, function
            # we will apend target in list
            if all_conditional_edges[conditional_edge][0]['condition_type'] == 'list':
                conditional_list=[]
                edge_source, edge_function = conditional_edge
                for edge in all_conditional_edges[conditional_edge]:
                    conditional_list.append(edge['target'])

                function_ref = get_function_reference(edge_function)
                workflow.add_conditional_edges(edge_source, function_ref, conditional_list)

        return workflow,input_var_dict,


    else:
      return workflow,input_var_dict,


def graph_builder(input_json):
  if input_json != None :
    workflow,input_dict, = build_graph_from_json(app_json = input_json)
    app = workflow.compile()
    # extracting nodes order
    first_json_key = list(input_json.keys())[0]
    current_app_json = input_json[first_json_key]
    node_list = extract_nodes(current_app_json)
    print(f"The Nodes are(In order):\n {node_list}")
    return app,input_dict,node_list
    # return app,input_dict
  else:
      return "Error: input_json is None or empty. Please provide a valid input JSON."
  


#**what poits should add in documentation**
# define the json structure properly
# define which workflow json will be at top-level 
# define which nodes come firest such as graph nodes then runnable nodes then start/end nodes
# and subgraphs would be the sub-graph json with same name of node
# -----
# add the acuurate format of workflow-json into a graphConfigs file
# add nodes function in workflownodes
# add state-classses in graphstates
# register both classess and function in registry file
# then use run workflow file to execute the workflow



#**Improvements**
# improve for the extract node function for parallel workflows
# check the multiple nodes with same names such as in gumloop
# check for 3 leval sub-graphs