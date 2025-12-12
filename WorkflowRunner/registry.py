# File Name: function_registry.py
# Purpose: Register all functions in a central registry for easy access.

# ____________________

# file : functionRegistry.py

from typing import Dict, TypedDict, Optional, Callable
from workflowNodes import *
from graphStates import *
# from subWorkflowNodes import *

function_registry = {
    "write_post": write_post,
    "response_1": response_1,
    "response_2": response_2,
    "model": call_model
}


def get_function_reference(function_name: str) -> Callable:
    # function_registry=get_registry_dict()
    return function_registry.get(function_name, lambda: None)


# class refrence
class_registry = {
    "q1_state": q1_state,
    "output_q1_state": output_q1_state,
    "q2_state":q2_state,
    "output_q2_state":output_q2_state,
    "finalState":finalState
}


def get_class_reference(class_name: str) -> Callable:
    # function_registry=get_registry_dict()
    # return class_registry.get(class_name, lambda: None)
    return class_registry.get(class_name)

