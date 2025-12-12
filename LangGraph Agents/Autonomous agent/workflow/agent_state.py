from typing import TypedDict, List, Dict, Optional

# Agent state definition
class AgentState(TypedDict):
    task: str
    allowed_nodes: List[str]
    available_nodes: List[Dict]
    subtasks: List[str]
    subtask_sequence: List[str]
    subtask_node_map: Dict[str, List[Dict]]
    plan: List[Dict]
    context: str
    current_step: int
    workflow_valid: Optional[bool]
    final_workflow: Optional[Dict]
    evaluation: dict
    replan_attempts: int
    
    # initial_workflow: List[Dict]
    initial_workflow: Optional[Dict]
    missing_nodes: Optional[List[Dict]]
    missing_node_error: Optional[bool]
