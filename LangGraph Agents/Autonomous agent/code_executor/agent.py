# File: src/agent.py
"""
Agent Functions

Implements the logic for creating workflow and node definitions from user requests.
"""

import pathlib
import sys
from venv import logger
import logging
logger = logging.getLogger("AgenticWorkflow")
logger.setLevel(logging.INFO)
# from code_writer import CodeAgent
from code_executor.common import InvalidInputError
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import datetime
import random
import string
from workflow.workflow_generator_main import Workflow_generator_v1



import datetime
from typing import List, Dict, Any, Optional
# from .common import logger, InvalidInputError, validate_json_schema
# from code_writer import CodeAgent
# from .workflow_generator import generate_workflow
import json

random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))


def create_workflow_agent(user_request: str, list_allowed_nodes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generates a workflow JSON based on a user request and allowed nodes.
    
    Validates input using JSON schema and constructs the workflow data.
    
    :param user_request: A string describing the workflow request.
    :param list_allowed_nodes: A list of allowed node names for workflow steps.
    :param list_allowed: A list of allowed operations or permissions.
    :return: A dictionary representing the workflow JSON.
    :raises InvalidInputError: On input validation failure.
    
    @Feature Workflow Creation & Versioning
    @Scenario Successfully create a workflow with valid input / Creation fails with malformed JSON / Creation fails with missing required fields
    """

    try:
        new_workflow = Workflow_generator_v1(user_request, list_allowed_nodes)
        workflow_reponse, orig_user_task, descriptions, tags, spo, status = new_workflow.generate_workflow_v1()
        if status =="complete_workflow":
            workflow_data = {
                "name": f"Workflow_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{random_suffix}",
                "data": workflow_reponse , # Workflow JSON string,
                "orig_user_task": orig_user_task,
                "descriptions": descriptions,
                "tags": tags,
                "spo": spo,
                "status": "workflow_created",

            }

            logger.info("Workflow generated successfully: %s", workflow_data["name"])
            return workflow_data
        else:

            missing_nodes = {
                "name": f"Workflow_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{random_suffix}",
                "data": workflow_reponse , # Workflow JSON string,
                "orig_user_task": orig_user_task,
                "descriptions": descriptions,
                "tags": tags,
                "spo": spo,
                "status": "missing_nodes"
            }

            logger.info("Missing Nodes Detected: %s", missing_nodes["name"])
            return missing_nodes

            
        
    except Exception as e:
        logger.exception("Error in create_workflow_agent")
        raise InvalidInputError(f"Workflow agent error: {e}")

# def create_node_agent(Function_Description: str, Function_Inputs: List[str], Function_Ouput: str, node_name: str, bucket_uri: str,tenant_id:str, Edit_Code: bool = False) -> Dict[str, Any]:
#     try:
#         initial_state = {
#             "Function_Description": Function_Description,
#             "Function_Inputs": Function_Inputs,
#             "Function_Output": Function_Ouput,
#             "bucket_uri": bucket_uri,
#             "tenant_id":  tenant_id, 
#             "edit_code" : Edit_Code,
#         }
#         agent = CodeAgent()
#         final_state = agent.run(initial_state)
#         print(f"------------------------------------")
#         print(final_state)
#         print(f"------------------------------------")
#         final_code = ""
#         if "code_2" in final_state:
#             code2 = final_state["code_2"]
#             if isinstance(code2, dict) and "changes" in code2:
#                 changes = code2["changes"]
#                 if isinstance(changes, list) and len(changes) > 0:
#                     final_code = changes[0].get("content", "")
#         # Fallback to code_1 if no code from code_2 is available.
#         if not final_code and "code_1" in final_state:
#             code1 = final_state["code_1"]
#             if isinstance(code1, dict) and "changes" in code1:
#                 changes = code1["changes"]
#                 if isinstance(changes, list) and len(changes) > 0:
#                     final_code = changes[0].get("content", "")
#         # Print the final state for debugging
#         print("DEBUG - Final state from agent.run():")
#         print(json.dumps({k: str(v)[:100] + '...' if isinstance(v, str) and len(str(v)) > 100 else v 
#                          for k, v in final_state.items() if k not in ['code_2']}, indent=2))
        
#         # Get node_uri and node_metadata
#         node_uri = final_state.get("node_uri", "")
#         node_metadata = final_state.get("node_metadata", {})
        
#         print(f"DEBUG - node_uri: {node_uri}")
#         print(f"DEBUG - node_metadata type: {type(node_metadata)}")
#         print(f"DEBUG - node_metadata: {node_metadata}")
        
#         # Parse metadata if it's a string
#         if isinstance(node_metadata, str):
#             try:
#                 node_metadata = json.loads(node_metadata)
#                 print("DEBUG - Successfully parsed node_metadata from string to dict")
#             except Exception as e:
#                 print(f"DEBUG - Failed to parse node_metadata: {e}")
#                 node_metadata = {}
        

#         node_data = {
#             "name": node_name,
#             "code": final_code,
#             "uri": node_uri,
#             "node_metadata": node_metadata,
#             "timestamp": datetime.datetime.now(datetime.timezone.utc)
#         }
        
#         print("DEBUG - Final node_data to be returned:")
#         print(json.dumps(node_data, default=str, indent=2))
        
#         logger.info("Node generated successfully: %s", node_name)
#         return node_data
#     except Exception as e:
#         logger.exception("Node payload validation failed")
#         raise InvalidInputError(f"Node validation error: {e}")
#     # In a production scenario, duplicate checks would occur at the persistence layer.
#     # Here we assume the caller checks for duplicates.
    