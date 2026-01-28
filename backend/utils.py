"""
UTILS — AI VOICE BOT
Purpose:
- Conditional edges handling
- Pause / resume helpers
- Interrupt node detection
- Graph execution safety
"""

from typing import Dict, List, Tuple


# ---------------------------------------------------
# 1️⃣ GROUP CONDITIONAL EDGES
# ---------------------------------------------------
# LangGraph ke conditional edges ko group karta hai
# Key = (source_node, decision_function)

def group_by_source_and_function(edges: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
    grouped = {}

    for edge in edges:
        key = (edge["source"], edge["function"])
        grouped.setdefault(key, []).append(edge)

    return grouped


# ---------------------------------------------------
# 2️⃣ INTERRUPT / PAUSE NODES
# ---------------------------------------------------
# Voice workflow mein yahi sab se important hai

INTERRUPT_NODES = {
    "listen",           # user bolne ka wait
    "wait_for_user",
    "hold_call",
}


def is_interrupt_node(node_id: str) -> bool:
    """
    Check karta hai kya node workflow ko pause karega
    """
    return node_id in INTERRUPT_NODES


# ---------------------------------------------------
# 3️⃣ WORKFLOW PAUSED?
# ---------------------------------------------------
# State-based pause detection

def is_workflow_paused(state: Dict) -> bool:
    """
    True agar workflow pause mein hai
    """
    return bool(state.get("is_paused", False))


# ---------------------------------------------------
# 4️⃣ SAFE STATE MERGE
# ---------------------------------------------------
# Node outputs ko safely state mein merge karta hai

def merge_state(old_state: Dict, new_values: Dict) -> Dict:
    """
    Old state + node output ko merge karta hai
    """
    updated = old_state.copy()
    updated.update(new_values)
    return updated


# ---------------------------------------------------
# 5️⃣ NEXT NODE VALIDATION
# ---------------------------------------------------
# decide_next node jo string return karta hai
# usko verify karta hai

def validate_next_node(next_node: str, allowed_nodes: List[str]) -> str:
    if next_node not in allowed_nodes:
        raise ValueError(f"Invalid next node: {next_node}")
    return next_node


# ---------------------------------------------------
# 6️⃣ SESSION / CALL HELPERS
# ---------------------------------------------------

def init_call_state(payload: Dict) -> Dict:
    """
    Webhook se initial call state banata hai
    """
    return {
        "call_id": payload["call_id"],
        "phone": payload["phone"],
        "bot_text": "Assalam-o-Alaikum!",
        "user_response": "",
        "intent": None,
        "score": 0,
        "qualified": False,
        "is_paused": False,
        "waiting_for": None,
        "current_node": "__start__",
    }



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