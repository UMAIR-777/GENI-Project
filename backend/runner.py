# File: runner.py
# Purpose: Execute LangGraph workflows asynchronously with pause/resume support
# --------------------------------------------------

from typing import Dict
from backend.json_to_langgraph import StateGraph, START, END
from db.repository import save_lead # Your own persistence logic
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("LangGraphRunner")


async def run_workflow(app: StateGraph, state: Dict) -> Dict:
    """
    Async runner for workflows with execution tracing.
    """

    logger.info("▶️ Starting workflow execution")

    async for step in app.astream(state):

        state = step
        current_node = state.get("current_node")

        if current_node:
            logger.info(f"➡️ Executing node: {current_node}")

        # Pause handling
        if state.get("is_paused"):
            logger.info(f"⏸ Workflow paused at node: {current_node}")
            save_lead(state["call_id"], state)
            return state

    logger.info("✅ Workflow completed successfully")
    return state

