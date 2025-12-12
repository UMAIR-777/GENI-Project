import json
import logging
import os
import psycopg2
from dotenv import load_dotenv
from dataclasses import dataclass
from .agent_state import AgentState
from langgraph.graph import StateGraph
from typing import List, Dict, Any, Optional, Tuple, Literal
from .embedding_service import EmbeddingService
from huggingface_hub import InferenceClient
from .node_service import NodeService
from .workflow_planner import WorkflowPlanner
from .DATA_FOLDER.save_available_nodes import AVAILABLE_NODES
from .database_manager import DatabaseManager


# -----------------------------------------------------------------------------
# Global Configuration and Common Components
# -----------------------------------------------------------------------------

# Load environment variables from .env file
load_dotenv()

# Configure logging for production quality. Logging should integrate with centralized systems (e.g., ELK, Sentry)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Custom Exceptions and Data Types
# -----------------------------------------------------------------------------

class WorkflowError(Exception):
    """
    Custom exception raised for errors in workflow processing.
    
    This exception is used to indicate critical failures in workflow generation,
    retrieval, or persistence that might lead to catastrophic outcomes if not handled.
    """
    pass

@dataclass
class Workflow:
    """
    Data class representing a workflow with state, nodes, edges, and missing nodes.

    @Feature: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
    @Scenario: Integrity of Workflow JSON Normalization

    Attributes:
        state (Dict[str, Any]): The current state of the workflow.
        nodes (List[Any]): List of workflow nodes.
        edges (List[Any]): List of connections between nodes.
        missing_nodes (List[Dict[str, Any]]): List of missing nodes, if any.
    """
    state: Dict[str, Any]
    nodes: List[Any]
    edges: List[Any]
    missing_nodes: List[Dict[str, Any]] = None

    def normalize(self) -> Dict[str, Any]:
        """
        Normalize the workflow into a JSON-compatible dictionary ensuring that
        all keys are present and of the correct type.

        @Feature: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
        @Scenario: Integrity of Workflow JSON Normalization

        Returns:
            Dict[str, Any]: A normalized workflow dictionary.
        """
        normalized = {
            "state": self.state if isinstance(self.state, dict) else {},
            "nodes": self.nodes if isinstance(self.nodes, list) else [],
            "edges": self.edges if isinstance(self.edges, list) else [],
            "missing_nodes": self.missing_nodes if isinstance(self.missing_nodes, list) else []
        }
        return normalized

class WorkflowGenerator:
    """
    Coordinates the overall process of generating the final workflow.
    """
    def __init__(self, ai_service, template_renderer, database_manager, embedding_service, workflow_planner, node_service):
        self.ai_service = ai_service
        self.template_renderer = template_renderer
        self.database_manager = database_manager
        self.embedding_service = embedding_service
        self.workflow_planner = workflow_planner
        self.node_service = node_service
    
    def create_planning_workflow(self):
        """Creates the planning workflow using StateGraph."""
        workflow = StateGraph(AgentState)
        workflow.add_node("init", self.workflow_planner.initialize_state)
        workflow.add_node("decompose", self.workflow_planner.decompose_task)
        workflow.add_node("planning", self.workflow_planner.generate_plan_batch)
        workflow.add_node("execute", self.workflow_planner.execute_step)
        workflow.add_node("finalize", self.workflow_planner.finalize)
        workflow.add_node("finalize_missing", self.workflow_planner.finalize_missing)
        
        # Unconditional edges before:
        workflow.add_edge("init", "decompose")
        workflow.add_edge("decompose", "planning")

        
        # Define conditional branch from planning
        def decide_next_step_plan(state: AgentState) -> Literal["execute", "finalize_missing"]:
            if state.get("missing_node_error") is True:
                return "finalize_missing"
            return "execute"
        
        # Define conditional branch from execute
        def decide_next_step(state: AgentState) -> Literal["planning", "execute", "finalize"]:
            if state.get("workflow_valid") is False:
                return "planning"
            elif state["current_step"] >= len(state["plan"]):
                return "finalize"
            return "execute"
        
        # Add conditional edges (these will ensure only a single branch is selected)
        workflow.add_conditional_edges("planning", decide_next_step_plan, {"execute": "execute", "finalize_missing": "finalize_missing"})
        workflow.add_conditional_edges("execute", decide_next_step, {"planning": "planning", "execute": "execute", "finalize": "finalize"})
        workflow.set_entry_point("init")
        try:
            compiled = workflow.compile()
            # logger.info("Planning workflow compiled successfully with entry point 'init'.")
            return compiled
        except Exception as e:
            # logger.error(f"Failed to compile planning workflow: {e}")
            raise RuntimeError("Workflow compilation failed.") from e
    
# -----------------------------------------------------------------------------
# Core Workflow Management Functions
# -----------------------------------------------------------------------------

    def generate_workflow(self, user_task: str, allowed_nodes: Optional[List[str]] = None) -> Tuple[Any, ...]:
        """
        Generate a workflow based on a user task. Retrieves existing similar workflows or creates a new one,
        enriches it with AI-generated metadata (descriptions, tags, spo), and returns all relevant data.

        Returns:
            Tuple containing:
                - final_workflow_data (JSON string or list of missing nodes)
                - user_task (str)
                - descriptions (List[str])
                - tags (List[str])
                - spo (Dict[str, Any])
                - status (str): "completed_workflow" or "missing_nodes"
        """
        # Input validation
        if not isinstance(user_task, str) or not user_task.strip():
            raise ValueError("User task must be a valid non-empty string.")

        # Attempt retrieval of similar workflow
        similar_workflows = self.database_manager.retrieve_similar_workflow(
            user_task,
            top_k=1,
            similarity_threshold=0.9
        )
        if similar_workflows:
            logger.info("Similar workflow found; returning existing workflow without AI-enrichment.")
            entry = similar_workflows[0]
            workflow_obj = entry["workflow"]
            # Initialize empty metadata for existing workflows
            return json.dumps(workflow_obj, indent=4), user_task, [], [], {}, "completed_workflow"

        # Build initial planning state
        initial_state = {
            "task": user_task,
            "allowed_nodes": allowed_nodes or [],
            "available_nodes": [],
            "subtasks": [],
            "subtask_sequence": [],
            "subtask_node_map": {},
            "plan": [],
            "context": "",
            "current_step": 0,
            "workflow_valid": None,
            "evaluation": {},
            "replan_attempts": 0,
            "final_workflow": {},
            "missing_nodes": [],
            "missing_node_error": False,
            "initial_workflow": {},
        }

        # Execute planning workflow
        try:
            planning_workflow = self.create_planning_workflow()
            try:
                final_state = planning_workflow.invoke(initial_state, {"recursion_limit": 100})
            except psycopg2.Error as e:
                if e.pgcode == '42P01':  # missing table
                    logger.info("Table 'node_embeddings' missing during planning; using fallback.")
                    final_state = initial_state
                else:
                    logger.error("Database error during planning: %s", e)
                    raise WorkflowError("Workflow planning failed") from e
        except Exception as e:
            logger.error("Critical error in planning workflow: %s", e)
            raise WorkflowError("Workflow planning failed") from e


        # Extract final workflow and missing nodes
        final_workflow_data = final_state.get('final_workflow', {})
        missing_nodes = final_state.get('missing_nodes', [])


        if final_workflow_data:
            # Serialize workflow
            workflow_json = json.dumps(final_workflow_data)

            # Use AI service to generate metadata
            try:
                prompt = self.template_renderer.render_prompt(
                    "create_blueprint_usertask.jinja2",
                    task=user_task,
                )
                response = self.ai_service.ask_ai(prompt, context="Return valid JSON with descriptions, tags, spo")
                metadata = json.loads(response)
                descriptions = metadata.get('descriptions', [])
                tags = metadata.get('tags', [])
                spo = metadata.get('spo', {})
            except Exception as e:
                logger.error("Error generating AI metadata: %s", e)
                descriptions, tags, spo = [], [], {}


            # Return enriched workflow
            return workflow_json, user_task, descriptions, tags, spo, "completed_workflow"
        else:
            # No workflow generated; return missing nodes
            return missing_nodes, user_task, [], [], {}, "missing_nodes"


