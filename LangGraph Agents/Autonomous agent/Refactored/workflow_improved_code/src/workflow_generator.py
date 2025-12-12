# import json
# import logging
# # import os
# import psycopg2
# from dotenv import load_dotenv
# from dataclasses import dataclass
# from agent_state import AgentState
# from langgraph.graph import StateGraph
# from typing import List, Dict, Any, Optional, Tuple, Literal
# # from src.embedding_service import EmbeddingService
# from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES
# # from .database_manager import DatabaseManager

# # -----------------------------------------------------------------------------
# # Global Configuration and Common Components
# # -----------------------------------------------------------------------------

# # Load environment variables from .env file
# load_dotenv()

# # Configure logging for production quality. Logging should integrate with centralized systems (e.g., ELK, Sentry)
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
# logger = logging.getLogger(__name__)

# # -----------------------------------------------------------------------------
# # Custom Exceptions and Data Types
# # -----------------------------------------------------------------------------

# class WorkflowError(Exception):
#     """
#     Custom exception raised for errors in workflow processing.
    
#     This exception is used to indicate critical failures in workflow generation,
#     retrieval, or persistence that might lead to catastrophic outcomes if not handled.
#     """
#     pass

# @dataclass
# class Workflow:
#     """
#     Data class representing a workflow with state, nodes, edges, and missing nodes.

#     @Feature: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
#     @Scenario: Integrity of Workflow JSON Normalization

#     Attributes:
#         state (Dict[str, Any]): The current state of the workflow.
#         nodes (List[Any]): List of workflow nodes.
#         edges (List[Any]): List of connections between nodes.
#         missing_nodes (List[Dict[str, Any]]): List of missing nodes, if any.
#     """
#     state: Dict[str, Any]
#     nodes: List[Any]
#     edges: List[Any]
#     missing_nodes: List[Dict[str, Any]] = None

#     def normalize(self) -> Dict[str, Any]:
#         """
#         Normalize the workflow into a JSON-compatible dictionary ensuring that
#         all keys are present and of the correct type.

#         @Feature: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
#         @Scenario: Integrity of Workflow JSON Normalization

#         Returns:
#             Dict[str, Any]: A normalized workflow dictionary.
#         """
#         normalized = {
#             "state": self.state if isinstance(self.state, dict) else {},
#             "nodes": self.nodes if isinstance(self.nodes, list) else [],
#             "edges": self.edges if isinstance(self.edges, list) else [],
#             "missing_nodes": self.missing_nodes if isinstance(self.missing_nodes, list) else []
#         }
#         return normalized

# class WorkflowGenerator:
#     """
#     Coordinates the overall process of generating the final workflow.
#     """
#     def __init__(self, ai_service, template_renderer, database_manager, embedding_service, workflow_planner, node_service):
#         self.ai_service = ai_service
#         self.template_renderer = template_renderer
#         self.database_manager = database_manager
#         self.embedding_service = embedding_service
#         self.workflow_planner = workflow_planner
#         self.node_service = node_service
    
#     def create_planning_workflow(self) -> Any:
#         """
#         Create and compile the planning workflow using StateGraph.

#         @Feature: Agent State Management and Workflow Planning
#         @Scenario: Compile a planning workflow with proper node and edge configuration

#         Returns:
#             Any: A compiled workflow object ready for execution.

#         Raises:
#             RuntimeError: If the workflow compilation fails.
#         """
#         try:
#             workflow = StateGraph(AgentState)
#             workflow.add_node("init", self.workflow_planner.initialize_state)
#             workflow.add_node("decompose", self.workflow_planner.decompose_task)
#             workflow.add_node("planning", self.workflow_planner.generate_plan_batch)
#             workflow.add_node("execute", self.workflow_planner.execute_step)
#             workflow.add_node("finalize", self.workflow_planner.finalize)

#             workflow.add_edge("init", "decompose")
#             workflow.add_edge("decompose", "planning")
#             workflow.add_edge("planning", "execute")

#             def decide_next_step(state: AgentState) -> Literal["planning", "execute", "finalize"]:
#                 # Backward-chaining decision logic: if workflow invalid, replan; if all steps executed, finalize.
#                 if state.get("workflow_valid") is False:
#                     return "planning"
#                 elif state.get("current_step", 0) >= len(state.get("plan", [])):
#                     return "finalize"
#                 return "execute"

#             workflow.add_conditional_edges("execute", decide_next_step,
#                                         {"planning": "planning", "execute": "execute", "finalize": "finalize"})
#             workflow.set_entry_point("init")
#             compiled = workflow.compile()
#             # logger.info("Planning workflow compiled successfully with entry point 'init'.")
#             return compiled
#         except Exception as e:
#             # logger.error(f"Failed to compile planning workflow: {e}")
#             raise RuntimeError("Workflow compilation failed.") from e

#     def create_planning_workflow(self):
#         """Creates the planning workflow using StateGraph."""
#         workflow = StateGraph(AgentState)
#         workflow.add_node("init", self.workflow_planner.initialize_state)
#         workflow.add_node("decompose", self.workflow_planner.decompose_task)
#         workflow.add_node("planning", self.workflow_planner.generate_plan_batch)
#         workflow.add_node("execute", self.workflow_planner.execute_step)
#         workflow.add_node("finalize", self.workflow_planner.finalize)
#         workflow.add_node("finalize_missing", self.workflow_planner.finalize_missing)
        
#         # Unconditional edges before:
#         workflow.add_edge("init", "decompose")
#         workflow.add_edge("decompose", "planning")

        
#         # Define conditional branch from planning
#         def decide_next_step_plan(state: AgentState) -> Literal["execute", "finalize_missing"]:
#             if state.get("missing_node_error") is True:
#                 return "finalize_missing"
#             return "execute"
        
#         # Define conditional branch from execute
#         def decide_next_step(state: AgentState) -> Literal["planning", "execute", "finalize"]:
#             if state.get("workflow_valid") is False:
#                 return "planning"
#             elif state["current_step"] >= len(state["plan"]):
#                 return "finalize"
#             return "execute"
        
#         # Add conditional edges (these will ensure only a single branch is selected)
#         workflow.add_conditional_edges("planning", decide_next_step_plan, {"execute": "execute", "finalize_missing": "finalize_missing"})
#         workflow.add_conditional_edges("execute", decide_next_step, {"planning": "planning", "execute": "execute", "finalize": "finalize"})
#         workflow.set_entry_point("init")
#         try:
#             compiled = workflow.compile()
#             # logger.info("Planning workflow compiled successfully with entry point 'init'.")
#             return compiled
#         except Exception as e:
#             # logger.error(f"Failed to compile planning workflow: {e}")
#             raise RuntimeError("Workflow compilation failed.") from e
    
# # -----------------------------------------------------------------------------
# # Core Workflow Management Functions
# # -----------------------------------------------------------------------------

#     def generate_workflow(self, user_task: str, allowed_nodes: Optional[List[str]] = None) -> Tuple[str, List[Dict[str, Any]]]:
#         """
#         Generate a workflow based on a user task. This function attempts to retrieve an existing
#         workflow from the database that matches the task using vector similarity. If none exists,
#         it generates a new workflow via a planning engine, validates and normalizes it, and saves it.

#         Args:
#             user_task (str): A non-empty string describing the user task.
#             allowed_nodes (Optional[List[str]]): An optional list of allowed nodes for workflow generation.

#         Returns:
#             Tuple[str, List[Dict[str, Any]]]:
#                 - The normalized workflow as a JSON string.
#                 - A list of missing nodes (if any).

#         Raises:
#             ValueError: If the user_task is not a valid non-empty string.
#             WorkflowError: If workflow planning, retrieval, or persistence fails.
#         """
#         # Input validation
#         if not isinstance(user_task, str) or not user_task.strip():
#             raise ValueError("User task must be a valid non-empty string.")

#         # Attempt to retrieve a similar workflow from the database.
#         similar_workflows = self.database_manager.retrieve_similar_workflow(user_task, top_k=1, similarity_threshold=0.9)

#         if similar_workflows:
#             # Unpack values from the first matching workflow (if found)
#             logger.info("Similar workflow found; returning existing workflow.")
#             try:
#                 wf_id, desc, workflow_obj, sim = similar_workflows[0]  # Unpack workflow details
#             except ValueError:
#                 logger.error("Unexpected unpacking issue with similar workflows.")
#                 return {}, []

#             # Create a properly structured workflow JSON
#             normalized_workflow = {
#                 "main": {
#                     "state": workflow_obj.state,
#                     "nodes": workflow_obj.nodes,
#                     "edges": workflow_obj.edges
#                 },
#             }
            
#             # Debug logging
#             logger.info(f"Returning existing workflow: {json.dumps(normalized_workflow, indent=2)}")
#             return json.dumps(normalized_workflow, indent=4), []

#         # If no similar workflow is found, proceed to generate a new workflow.
#         logger.info("No similar workflows found; generating a new workflow.")
        
#         # Initialize the initial state for a new workflow.
#         initial_state = {
#             "task": user_task,
#             "allowed_nodes": allowed_nodes if allowed_nodes is not None else [],
#             "available_nodes": [],
#             "subtasks": [],
#             "subtask_sequence": [],
#             "subtask_node_map": {},
#             "plan": [],
#             "context": "",
#             "current_step": 0,
#             "workflow_valid": None,
#             "evaluation": {},
#             "replan_attempts": 0,
#             "final_workflow": {},
#             "missing_nodes": [],
#             "missing_node_error": False,
#             "initial_workflow": {},
#         }

#         # Generate node embeddings for available nodes.
#         try:
#             # generate_and_store_node_embeddings internally validates and persists embeddings.
#             self.embedding_service.generate_and_store_node_embeddings(AVAILABLE_NODES)
#         except psycopg2.Error as e:
#             if e.pgcode == '42P01':
#                 logger.info("Table 'node_embeddings' missing; skipping node embedding generation.")
#             else:
#                 logger.error("Critical database error during node embedding generation: %s", e)
#                 raise WorkflowError("Node embedding generation failed") from e
#         except Exception as e:
#             logger.info("Non-critical error during node embedding generation: %s", e)

#         # Generate the planning workflow using the planning engine.
#         try:
#             planning_workflow = self.create_planning_workflow()
#             logger.info("Planning Workflow: %s", planning_workflow)
            
#             try:
#                 final_state = planning_workflow.invoke(initial_state, {"recursion_limit": 100})
#             except psycopg2.Error as e:
#                 if e.pgcode == '42P01':
#                     logger.info("Table 'node_embeddings' missing during planning; using fallback workflow.")
#                     final_state = initial_state
#                 else:
#                     logger.error("Database error during planning: %s", e)
#                     raise WorkflowError("Workflow planning failed") from e
#         except Exception as e:
#             logger.error("Critical error in planning workflow: %s", e)
#             raise WorkflowError("Workflow planning failed") from e

#         # Handle the result and process the final workflow
#         result_workflow = None
#         result_missing_nodes = []

#         try:
#             final_workflow_data = final_state.get('final_workflow', {})
#             missing_nodes = final_state.get('missing_nodes', [])
            
#             if missing_nodes:
#                 logger.info(f"Missing nodes detected: {missing_nodes}")
#                 result_missing_nodes = missing_nodes
#             elif final_workflow_data:
#                 try:
#                     # Remove missing_nodes before formatting
#                     if "missing_nodes" in final_workflow_data:
#                         del final_workflow_data["missing_nodes"]
                    
#                     # Format workflow with proper indentation
#                     result_workflow = json.dumps(final_workflow_data, indent=2)
                    
#                     # Attempt to save workflow
#                     try:
#                         self.database_manager.save_workflow(user_task, result_workflow, [])
#                         logger.info("Workflow saved successfully to database")
#                     except Exception as e:
#                         logger.warning(f"Non-critical error saving workflow: {e}")
#                 except Exception as e:
#                     logger.error(f"Error processing final workflow: {e}")
#                     raise WorkflowError("Failed to process workflow") from e
#             else:
#                 logger.warning("No workflow data generated")
                    
#         except Exception as e:
#             logger.error(f"Critical error in workflow generation: {e}")
#             raise WorkflowError("Workflow generation failed") from e

#         return result_workflow, result_missing_nodes


import json
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Literal
from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES
import psycopg2
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from agent_state import AgentState
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from z3 import Solver, Int, And

# -----------------------------------------------------------------------------
# Common Types and Exceptions
# -----------------------------------------------------------------------------

class WorkflowError(Exception):
    """
    Custom exception for critical workflow failures.
    """
    pass

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

# -----------------------------------------------------------------------------
# Constraint Validation using Z3
# -----------------------------------------------------------------------------

# def validate_state_constraints(state: Dict[str, Any]) -> None:
#     """
#     @Feature: Workflow Constraint Validation
#     @Scenario: Enforce valid numeric ranges for state parameters

#     Uses Z3 solver to ensure state['current_step'] and state['plan'] length constraints.

#     Raises:
#         WorkflowError: If constraints are violated.
#     """
#     solver = Solver()
#     current_step = Int('current_step')
#     plan_len = Int('plan_len')
#     solver.add(current_step >= 0)
#     solver.add(plan_len >= 0)
#     solver.add(current_step <= plan_len)
#     solver.add(current_step == state.get('current_step', 0))
#     solver.add(plan_len == len(state.get('plan', [])))
#     if solver.check().r != 1:
#         raise WorkflowError("State constraints violated: current_step out of bounds")

# -----------------------------------------------------------------------------
# Input Validation
# -----------------------------------------------------------------------------

def validate_user_task(user_task: Any) -> str:
    """
    Validate that user_task is a non-empty string.

    @Feature: Workflow Generation API
    @Scenario: Invalid input raises ValueError

    Args:
        user_task: Input provided by user.

    Returns:
        Trimmed user_task.

    Raises:
        ValueError: If user_task is not a non-empty string.
    """
    if not isinstance(user_task, str) or not user_task.strip():
        logger.error("Invalid user_task input: %r", user_task)
        raise ValueError("User task must be a valid non-empty string.")
    return user_task.strip()

# -----------------------------------------------------------------------------
# Workflow Generator
# -----------------------------------------------------------------------------

class WorkflowGenerator:
    """
    Coordinates retrieval, planning, and persistence of workflows.

    @Feature: Workflow Generation API
    @Scenario: End-to-end workflow orchestration
    """

    def __init__(
        self,
        ai_service: Any,
        template_renderer: Any,
        database_manager: Any,
        embedding_service: Any,
        workflow_planner: Any,
        node_service: Any,
    ) -> None:
        """
        Initialize dependencies for workflow generation.

        All components are injected to support testability and SOLID design.
        """
        self.ai_service = ai_service
        self.template_renderer = template_renderer
        self.database_manager = database_manager
        self.embedding_service = embedding_service
        self.workflow_planner = workflow_planner
        self.node_service = node_service

    # @retry(
    #     retry=retry_if_exception_type(psycopg2.OperationalError),
    #     stop=stop_after_attempt(3),
    #     wait=wait_exponential(multiplier=1, min=1, max=5),
    # )
    # def retrieve_similar(
    #     self, user_task: str
    # ) -> List[Tuple[Any, Any, Any, Any]]:
    #     """
    #     @Feature: Workflow Generation API
    #     @Scenario: Transient DB error retry success
    #     @Scenario: Database retrieve error fallback

    #     Retry retrieval of similar workflows on transient DB errors.

    #     Args:
    #         user_task: Validated task description.

    #     Returns:
    #         List of workflow tuples.

    #     Raises:
    #         psycopg2.OperationalError: After retry attempts.
    #     """
    #     return self.database_manager.retrieve_similar_workflow(
    #         user_task, top_k=1, similarity_threshold=0.9
    #     )

    def create_planning_workflow(self) -> StateGraph:
        """
        @Feature: Agent State Management and Workflow Planning
        @Scenario: Compile planning StateGraph with all nodes and edges
        @Scenario: Catastrophic planning failure raises WorkflowError

        Build and compile a StateGraph with conditional transitions.

        Returns:
            Compiled StateGraph.

        Raises:
            WorkflowError: On graph build or compile failure.
        """
        try:
            graph = StateGraph(AgentState)
            # Node definitions
            graph.add_node("init", self.workflow_planner.initialize_state)
            graph.add_node("decompose", self.workflow_planner.decompose_task)
            graph.add_node("planning", self.workflow_planner.generate_plan_batch)
            graph.add_node("execute", self.workflow_planner.execute_step)
            graph.add_node("finalize", self.workflow_planner.finalize)
            graph.add_node(
                "finalize_missing", self.workflow_planner.finalize_missing
            )

            # Unconditional edges
            graph.add_edge("init", "decompose")
            graph.add_edge("decompose", "planning")

            # Conditional logic
            def decide_plan(
                state: AgentState,
            ) -> Literal["execute", "finalize_missing"]:
                return (
                    "finalize_missing"
                    if state.get("missing_node_error")
                    else "execute"
                )

            def decide_execute(
                state: AgentState,
            ) -> Literal["planning", "execute", "finalize"]:
                if state.get("workflow_valid") is False:
                    return "planning"  # not_checked Unexecuted lines Missing lines
                if state.get("current_step", 0) >= len(
                    state.get("plan", [])
                ):
                    return "finalize"
                return "execute" # not_checked Unexecuted lines Missing lines

            graph.add_conditional_edges(
                "planning",
                decide_plan,
                {"execute": "execute", "finalize_missing": "finalize_missing"},
            )
            graph.add_conditional_edges(
                "execute",
                decide_execute,
                {"planning": "planning", "execute": "execute", "finalize": "finalize"},
            )

            graph.set_entry_point("init")
            return graph.compile()
        except Exception as e: 
            logger.error( 
                "Failed to compile planning workflow", exc_info=True
            )
            raise WorkflowError("Workflow compilation failed.") from e 

    def generate_workflow(self, user_task: str, allowed_nodes: Optional[List[str]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate a workflow based on a user task. This function attempts to retrieve an existing
        workflow from the database that matches the task using vector similarity. If none exists,
        it generates a new workflow via a planning engine, validates and normalizes it, and saves it.

        Args:
            user_task (str): A non-empty string describing the user task.
            allowed_nodes (Optional[List[str]]): An optional list of allowed nodes for workflow generation.

        Returns:
            Tuple[str, List[Dict[str, Any]]]:
                - The normalized workflow as a JSON string.
                - A list of missing nodes (if any).

        Raises:
            ValueError: If the user_task is not a valid non-empty string.
            WorkflowError: If workflow planning, retrieval, or persistence fails.
        """
        # Input validation
        if not isinstance(user_task, str) or not user_task.strip():
            raise ValueError("User task must be a valid non-empty string.")

        # Attempt to retrieve a similar workflow from the database.
        similar_workflows = self.database_manager.retrieve_similar_workflow(user_task, top_k=1, similarity_threshold=0.9)

        if similar_workflows:
            # Unpack values from the first matching workflow (if found)
            logger.info("Similar workflow found; returning existing workflow.")
            try:
                wf_id, desc, workflow_obj, sim = similar_workflows[0]  # Unpack workflow details
            except ValueError:
                logger.error("Unexpected unpacking issue with similar workflows.")
                return {}, []

            # Create a properly structured workflow JSON
            normalized_workflow = {
                "main": {
                    "state": workflow_obj.state,
                    "nodes": workflow_obj.nodes,
                    "edges": workflow_obj.edges
                },
            }
            
            # Debug logging
            logger.info(f"Returning existing workflow: {json.dumps(normalized_workflow, indent=2)}")
            return json.dumps(normalized_workflow, indent=4), []

        # If no similar workflow is found, proceed to generate a new workflow.
        logger.info("No similar workflows found; generating a new workflow.")
        
        # Initialize the initial state for a new workflow.
        initial_state = {
            "task": user_task,
            "allowed_nodes": allowed_nodes if allowed_nodes is not None else [],
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

        # Generate node embeddings for available nodes.
        try:
            # Directly call generate_and_store_node_embeddings with AVAILABLE_NODES
            self.embedding_service.generate_and_store_node_embeddings(AVAILABLE_NODES)
        except psycopg2.Error as e:
            if e.pgcode == '42P01':
                logger.info("Table 'node_embeddings' missing; skipping node embedding generation.") 
            else:
                logger.error("Critical database error during node embedding generation: %s", e) 
                raise WorkflowError("Node embedding generation failed") from e 
        except Exception as e:
            logger.info("Non-critical error during node embedding generation: %s", e)

        # Generate the planning workflow using the planning engine.
        try:
            planning_workflow = self.create_planning_workflow()
            logger.info("Planning Workflow: %s", planning_workflow)
            
            try:
                final_state = planning_workflow.invoke(initial_state, {"recursion_limit": 100})
            except psycopg2.Error as e:
                if e.pgcode == '42P01':
                    logger.info("Table 'node_embeddings' missing during planning; using fallback workflow.")
                    final_state = initial_state
                else:
                    logger.error("Database error during planning: %s", e)
                    raise WorkflowError("Workflow planning failed") from e
        except Exception as e:
            logger.error("Critical error in planning workflow: %s", e)
            raise WorkflowError("Workflow planning failed") from e

        # Handle the result and process the final workflow
        result_workflow = None
        result_missing_nodes = []

        try:
            final_workflow_data = final_state.get('final_workflow', {})
            missing_nodes = final_state.get('missing_nodes', [])
            
            if missing_nodes:
                logger.info(f"Missing nodes detected: {missing_nodes}")
                result_missing_nodes = missing_nodes
            elif final_workflow_data:
                try:
                    # Remove missing_nodes before formatting
                    if "missing_nodes" in final_workflow_data:
                        del final_workflow_data["missing_nodes"] 
                    
                    # Format workflow with proper indentation
                    result_workflow = json.dumps(final_workflow_data, indent=2)
                    
                    # Attempt to save workflow
                    try:
                        self.database_manager.save_workflow(user_task, result_workflow, [])
                        logger.info("Workflow saved successfully to database")
                    except Exception as e:
                        logger.warning(f"Non-critical error saving workflow: {e}")
                except Exception as e:
                    logger.error(f"Error processing final workflow: {e}")
                    raise WorkflowError("Failed to process workflow") from e
            else:
                logger.warning("No workflow data generated")
                    
        except Exception as e:
            logger.error(f"Critical error in workflow generation: {e}")
            raise WorkflowError("Workflow generation failed") from e

        return result_workflow, result_missing_nodes
