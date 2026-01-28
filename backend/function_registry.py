from backend.state_graphs import *
from typing import Dict, TypedDict, Optional, Callable
from backend.workflow_functions import (
    start_call,
    speak,
    listen,
    decide_next,
    end_call,
    qualify,   # <-- import the missing function
)

NODE_REGISTRY = {
    "start_call": start_call,
    "speak": speak,
    "listen": listen,
    "qualify": qualify,   # <-- add here
    "decide_next": decide_next,
    "end_call": end_call,
}

def get_function_reference(name: str):
    if name not in NODE_REGISTRY:
        raise ValueError(f"Unknown node: {name}")
    return NODE_REGISTRY[name]



class_registry = {"VoiceCallState" : VoiceCallState}

def get_class_reference(class_name: str) -> Callable:
    # function_registry=get_registry_dict()
    # return class_registry.get(class_name, lambda: None)
    return class_registry.get(class_name)