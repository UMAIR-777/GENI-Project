import pytest
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
from src.agent_state import AgentState

def decide_execute(state: AgentState) -> str:
    if state.get("workflow_valid") is False:
        return "planning"
    if state.get("current_step", 0) >= len(state.get("plan", [])):
        return "finalize"
    return "execute"

def test_decide_execute_branches():
    state = AgentState()
    # Test planning branch
    state["workflow_valid"] = False
    assert decide_execute(state) == "planning"

    # Test finalize branch
    state["workflow_valid"] = True
    state["current_step"] = 5
    state["plan"] = [1, 2, 3]
    assert decide_execute(state) == "finalize"

    # Test execute branch
    state["workflow_valid"] = True
    state["current_step"] = 1
    state["plan"] = [1, 2, 3]
    assert decide_execute(state) == "execute"
