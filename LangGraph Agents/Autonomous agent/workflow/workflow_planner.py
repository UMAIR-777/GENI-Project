import json
import os
import logging
from typing import List, Dict, Optional, Any, Tuple, Literal
from .agent_state import AgentState
from .ai_service import AIService
from .DATA_FOLDER.save_available_nodes import AVAILABLE_NODES
from .node_service import NodeService
from .embedding_service import EmbeddingService
from .database_manager import DatabaseManager
from huggingface_hub import InferenceClient

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)
client=None
class WorkflowPlanner:

    """
    Contains functions to decompose tasks, create initial workflows, execute steps,
    and map final edges. Uses available_nodes fetched from DB instead of static list.
    """
    def __init__(self,
                 template_renderer,
                 ai_service: AIService,
                 node_service: NodeService,
                 db_manager: DatabaseManager):
        self.template_renderer = template_renderer
        self.ai_service = ai_service
        self.node_service = node_service
        self.db_manager = db_manager

    def initialize_state(self, state: AgentState) -> AgentState:
        """
        Initialize the agent state with default values and load available_nodes from DB.
        """
        if not isinstance(state, dict):
            raise ValueError("Agent state must be a dictionary.")

        state.setdefault("task", "")
        state["allowed_nodes"] = state.get("allowed_nodes", [])
        state["subtasks"] = state.get("subtasks", [])
        state["subtask_sequence"] = state.get("subtask_sequence", [])
        state["subtask_node_map"] = state.get("subtask_node_map", {})
        state["plan"] = state.get("plan", [])
        state["context"] = state.get("context", "")
        state["current_step"] = state.get("current_step", 0)
        state["workflow_valid"] = state.get("workflow_valid", None)
        state["final_workflow"] = state.get("final_workflow", {})
        state["evaluation"] = state.get("evaluation", {})
        state["replan_attempts"] = state.get("replan_attempts", 0)
        state["initial_workflow"] = state.get("initial_workflow", {})
        state["missing_nodes"] = state.get("missing_nodes", [])
        state["missing_node_error"] = state.get("missing_node_error", False)
        # Fetch available nodes from the database
        state["available_nodes"] = self.db_manager.fetch_nodes()

        return state

    def decompose_task(self, state: AgentState) -> AgentState:
        """
        Decompose the main task in the agent state into subtasks using an AI-assisted prompt.
        
        @Feature: AI-Assisted Task Decomposition
        @Scenario: Decompose a complex user task into subtasks with a fallback to heuristic splitting
        
        Args:
            state (AgentState): The agent state containing a non-empty 'task' string.
        
        Returns:
            AgentState: The updated state with 'subtasks' and 'subtask_sequence' populated.
        
        Raises:
            ValueError: If 'task' is missing or empty in the state.
        """
        if "task" not in state or not isinstance(state["task"], str) or not state["task"].strip():
            raise ValueError("State must contain a non-empty 'task' string.")
        
        try:
            # Render the decomposition prompt using the proper template.
            prompt = self.template_renderer.render_prompt("subtask/decompose_task.jinja2", task=state["task"])

            print(f"prompt____________________________________: {prompt}")
        except Exception as e:
            # logger.error(f"Error rendering task decomposition prompt: {e}")
            raise RuntimeError("Failed to render task decomposition prompt.") from e

        try:
            # Invoke the LLM to get the decomposition result.
            response = self.ai_service.ask_ai(prompt, context="Return valid JSON")
            print(f"\nLLM response (decompose_task): {response}\n")  # Debugging line to check the raw response.
        except Exception as e:
            # logger.error(f"LLM invocation error during task decomposition: {e}")
            response = "{}"  # Fallback to empty JSON.

        try:
            result = json.loads(response)
            if "subtasks" not in result or "sequence" not in result:
                raise ValueError("AI response missing 'subtasks' or 'sequence' keys.")
            state["subtasks"] = result["subtasks"]
            state["subtask_sequence"] = result["sequence"]
        except Exception as e:
            # logger.error(f"Error parsing AI response: {e}")
            # Fallback heuristic: split the task on period delimiters.
            fallback_subtasks = [s.strip() for s in state["task"].split(".") if s.strip()]
            state["subtasks"] = fallback_subtasks
            state["subtask_sequence"] = fallback_subtasks
            # logger.info("Fallback decomposition applied due to parsing error.")
        
        return state


    def create_initial_subtask_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an initial subtask workflow blueprint based on the provided agent state.

        @Feature: Agent Workflow Blueprint Generation
        @Scenario: Successfully generate a subtask workflow blueprint via AI-assisted prompt rendering and JSON extraction
        @Scenario: Fall back to heuristic task splitting when the AI response is malformed

        Args:
            state (Dict[str, Any]): The current agent state. Must contain a non-empty 'task' key and may contain a 'subtasks' key.
        
        Returns:
            Dict[str, Any]: The updated agent state with a new 'plan' key that contains the workflow blueprint.
        
        Raises:
            ValueError: If the 'task' key is missing or is empty.
            RuntimeError: If rendering the blueprint prompt fails, if the LLM invocation fails, or if JSON parsing of the AI response fails.
        """
        # Input Validation
        if "task" not in state or not isinstance(state["task"], str) or not state["task"].strip():
            # logger.error("Agent state must include a non-empty 'task' string.")
            raise ValueError("Agent state must include a non-empty 'task' string.")

        # Render the blueprint prompt.
        try:
            prompt = self.template_renderer.render_prompt(
                "subtask/create_blueprint.jinja2",
                task=state["task"],
                subtasks=state.get("subtasks", [])
            )
            if not prompt.strip():
                # logger.error("Rendered blueprint prompt is empty.")
                raise RuntimeError("Blueprint prompt rendering produced an empty result.")
            # logger.info("Successfully rendered the blueprint prompt.")
        except Exception as e:
            # logger.error(f"Error rendering blueprint prompt: {e}")
            raise RuntimeError("Failed to render blueprint prompt.") from e

        # Query the LLM using the rendered prompt.
        try:
            response = self.ai_service.ask_ai(prompt, context="Return valid JSON")
            # logger.info("LLM returned a response for blueprint creation.")
            print(f"\nAI response for create_initial_subtask_workflow (blueprint): {response}\n")
        except Exception as e:
            # logger.error(f"LLM invocation failed during blueprint generation: {e}")
            raise RuntimeError("LLM invocation failed during blueprint generation.") from e

        # Attempt to parse the AI response as JSON.
        try:
            blueprint = json.loads(response)
            # Fix: Handle both array and object responses
            if isinstance(blueprint, list):
                # Convert array to object format
                blueprint = {"steps": blueprint}
                state["plan"] = blueprint["steps"]
            elif isinstance(blueprint, dict):
                state["plan"] = blueprint
            else:
                raise ValueError("Blueprint JSON must be an object or array")

            # Enrich each blueprint step with a 'description_embed' field.
            for step in state["plan"]:
                try:
                    # Convert spo dict to list format if needed
                    if isinstance(step.get("spo"), dict):
                        step["spo"] = [
                            step["spo"].get("subject", ""),
                            step["spo"].get("predicate", ""),
                            step["spo"].get("object", "")
                        ]

                    step_description = (
                        f"{step.get('step', '')}: "
                        f"input: {step.get('input', '')}; "
                        f"output: {step.get('output', '')}; "
                        f"tags: {', '.join(step.get('tags', []))}; "
                        f"description: {step.get('description', '')}; "
                        f"spo: {step.get('spo', '')}"
                    )
                    # print(f"\nStep description for embedding: {step_description}\n")
                    step["description_embed"] = step_description
                except Exception as inner_e:
                    # logger.warning(f"Failed to enrich blueprint step '{step.get('step', 'unknown')}': {inner_e}")
                    step["description_embed"] = ""
            # logger.info("Blueprint parsed and enriched successfully.")
        except Exception as e:
            # logger.error(f"Error parsing blueprint JSON: {e}")
            # Fallback: Use heuristic task splitting with validated BlueprintStep structure
            fallback_subtasks = [s.strip() for s in state["task"].split(".") if s.strip()]
            state["plan"] = [{
                "step": s,
                "input": [f"input_for_{s}"],
                "output": [f"output_for_{s}"],
                "tags": [f"tag_for_{s}"],
                "description": [f"Description for {s}"],
                "spo": ["Subject for " + s, "performs", "action for " + s],  # Changed to match BlueprintStep spo format
                "description_embed": f"{s}: Fallback embedding"
            } for s in fallback_subtasks]
            # logger.info("Fallback blueprint generated via task splitting.")
        
        return state

    def generate_plan_batch(self, state: AgentState) -> AgentState:
        """
        Generate a batch plan for the workflow by creating an initial subtask workflow,
        filtering nodes, and updating the agent state with a mapped plan.

        @Feature: Agent State Management and Workflow Planning
        @Scenario: Generate a complete plan using subtask workflows and node filtering

        Args:
            state (AgentState): The current agent state.

        Returns:
            AgentState: The updated state containing a generated plan, a mapping of nodes to subtasks, and missing nodes.

        Raises:
            RuntimeError: If node filtering or plan generation fails.
        """
        try:
            state = self.create_initial_subtask_workflow(state)
        except Exception as e:
            logger.error(f"Error during subtask workflow creation: {e}")
            raise RuntimeError("Subtask workflow creation failed.") from e

        state["initial_workflow"] = {
            "subtasks": state.get("subtask_sequence", []),
            "description": state.get("task", ""),
            "steps": [{"step": step.get("step", ""), "description": step.get("description", "")}
                    for step in state.get("plan", [])]
        }
        state["subtask_sequence"] = [step.get("step", "") for step in state.get("plan", [])]
        
        try:
            filtered_nodes_map, missing_nodes = self.node_service.filter_nodes_by_embedding_batch(state, state.get("plan", []),
                                                                                state.get("available_nodes", []))
        except Exception as e:
            logger.error(f"Error during node filtering: {e}")
            raise RuntimeError("Node filtering failed during plan generation.") from e

        if isinstance(filtered_nodes_map, str):
            print("Unable to generate nodes")  # This will be printed
            state["missing_node_error"] = True
            state['missing_nodes']=state['missing_nodes']

            return state
        else:
            state['subtask_node_map'] = filtered_nodes_map
    
        # state["subtask_node_map"] = filtered_nodes_map
        # state["missing_nodes"] = missing_nodes
        plan = []
        for step in state.get("plan", []):
            nodes = filtered_nodes_map.get(step.get("step", ""), [])
            if nodes:
                node_entry = {"node_id": nodes[0].get("id", ""), "inputs": nodes[0].get("input", []),
                            "output": nodes[0].get("output", [])}
                plan.append(node_entry)
            else:
                logger.warning(f"No nodes found for subtask '{step.get('step', '')}'.")
        state["plan"] = plan
        print(f"\n-------Generated plan-------: {state['plan']}\n")
        logger.info("Plan generated and state updated with node mappings and missing nodes.")
        return state

    def create_compiled_node(self, step: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """
        Create a compiled workflow node from a given plan step with proper input/output handling.
        
        @Feature: Agent State Management and Workflow Planning
        @Scenario: Convert plan steps into compiled nodes for workflow execution
        @Scenario: Handle both list and dictionary input/output formats robustly
        
        Args:
            step (Dict[str, Any]): A plan step dictionary containing 'node_id', 'inputs', and 'output'.
            state (AgentState): The current agent state for context.
        
        Returns:
            Dict[str, Any]: A compiled node dictionary.
        
        Raises:
            ValueError: If the step dictionary is missing required 'node_id' field.
        """
        if "node_id" not in step:
            raise ValueError("Workflow step missing 'node_id'.")
        
        # Handle inputs and outputs properly whether they're lists or dicts
        inputs = step.get("inputs", [])
        outputs = step.get("output", [])
        
        # Convert inputs/outputs to dict with empty string values
        input_dict = {k: "" for k in inputs} if isinstance(inputs, list) else inputs
        output_dict = {k: "" for k in outputs} if isinstance(outputs, list) else outputs
        
        return {
            "id": step["node_id"],
            "type": "runnable",
            "data": {"id": ["langgraph", "graph", "state", "CompiledStateGraph"], "name": step["node_id"]},
            "inputs": input_dict,
            "output": output_dict
        }

    def create_callable_node(self, step: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """
        Create a callable workflow node from a given plan step, ensuring proper input/output formatting.
        
        @Feature: Agent State Management and Workflow Planning
        @Scenario: Convert plan steps into callable nodes for workflow execution
        @Scenario: Ensure consistent input/output handling across node types
        
        Args:
            step (Dict[str, Any]): A plan step dictionary containing 'node_id', 'inputs', and 'output'.
            state (AgentState): The current agent state for context.
        
        Returns:
            Dict[str, Any]: A callable node dictionary.
        
        Raises:
            ValueError: If the step dictionary is missing required 'node_id' field.
        """
        if "node_id" not in step:
            raise ValueError("Workflow step missing 'node_id'.")
        
        # Handle inputs and outputs properly whether they're lists or dicts
        inputs = step.get("inputs", [])
        outputs = step.get("output", [])
        
        # Convert inputs/outputs to dict with empty string values
        input_dict = {k: "" for k in inputs} if isinstance(inputs, list) else inputs
        output_dict = {k: "" for k in outputs} if isinstance(outputs, list) else outputs
        
        return {
            "id": step["node_id"],
            "type": "runnable",
            "data": {"id": ["langgraph", "utils", "runnable", "RunnableCallable"], "name": step["node_id"]},
            "inputs": input_dict,
            "output": output_dict
        }

    def generate_workflow_from_plan(self, state: AgentState, plan: Optional[List[Dict[str, Any]]] = None,
                                    top_level: bool = True) -> Dict[str, Any]:
        """
        Generate a structured workflow JSON from the given plan. This function ensures the inclusion of special
        start and end nodes, builds the list of callable nodes for each plan step, and constructs edges connecting
        consecutive nodes.

        @Feature: Agent State Management and Workflow Planning
        @Scenario: Convert a plan into a structured workflow with nodes and edges, handling boundary conditions

        Args:
            state (AgentState): The current agent state.
            plan (Optional[List[Dict[str, Any]]]): An optional list of plan steps; if None, use state["plan"].
            top_level (bool): Indicates if this is a top-level workflow generation.

        Returns:
            Dict[str, Any]: A dictionary representing the final workflow JSON with keys 'state', 'nodes', and 'edges'.

        Raises:
            ValueError: If the plan is not a list.
        """
        # print(f"\nGenerated workflow from PLAN-------START: {plan}\n")
        if plan is None:
            plan = state.get("plan", [])
        if not isinstance(plan, list):
            raise ValueError("Plan must be a list of steps.")

        # Ensure start and end nodes are present.
        if not any(step.get("node_id") == "__start__" for step in plan):
            plan.insert(0, {"node_id": "__start__", "inputs": {}, "output": {}})
        if not any(step.get("node_id") == "__end__" for step in plan):
            plan.append({"node_id": "__end__", "inputs": {}, "output": {}})

        # Build callable nodes for plan steps excluding special nodes.
        nodes_list = [self.create_callable_node(step, state) for step in plan if step.get("node_id") not in ["__start__", "__end__"]]
        start_node = {"id": "__start__", "type": "schema", "data": "__start__"}
        end_node = {"id": "__end__", "type": "schema", "data": "__end__"}
        nodes_list.extend([start_node, end_node])

        # Construct edges connecting consecutive nodes.
        edges_list = []
        for i in range(len(plan) - 1):
            edge = {"source": plan[i].get("node_id", ""), "target": plan[i + 1].get("node_id", "")}
            edges_list.append(edge)

        workflow_json = {
            "main": {
            "state": {"mainstate": None, "inputstate": None, "outputstate": None},
            "nodes": nodes_list,
            "edges": edges_list
        }}
        # print(f"\nGenerated workflow JSON-------END: {workflow_json}\n")
        return workflow_json

    def map_workflow_edges(self, state: AgentState) -> AgentState:
        final_workflow = state["final_workflow"]
        prompt = self.template_renderer.render_prompt(
            "map_workflow_edges.jinja2",
            task=state['task'],
            initial_workflow=state['initial_workflow'],
            plan=state['plan'],
            final_workflow=final_workflow
        )
        print(f"map_workflow_edges prompt: {prompt}")
        workflow_json = self.ai_service.ask_ai(prompt, context="Return valid JSON")
        print(f"AI response for workflow mapping: {workflow_json}")
        try:
            mapped_workflow = json.loads(workflow_json)
            mapped_workflow['main']["state"]['mainstate'] = "GraphState"
            final_workflow['main']['state'] = mapped_workflow['main']['state']
            final_workflow['main']["edges"] = mapped_workflow['main']["edges"]
            state["final_workflow"] = final_workflow
        except Exception as e:
            print(f"Error in map_workflow_edges: {e}")
        return state

    def map_workflow_edges(self, state: AgentState) -> AgentState:
        
        """
        Map the edges of the final workflow using AI-assisted prompt generation via PromptManager.
        This function renders a prompt using state variables, sends it to the AI via Ask_AI, and
        validates the response to update the final workflow mapping.

        @Feature: Agent State Management and Workflow Planning
        @Scenario: Map workflow edges with AI-assisted prompt generation ensuring schema compliance

        Args:
            state (AgentState): The current agent state containing workflow data.

        Returns:
            AgentState: The updated state with a mapped final workflow.

        Raises:
            ValueError: If required state keys are missing or AI mapping fails.
        """
        try:
            final_workflow = state.get("final_workflow")
            missing_nodes = state.get("missing_nodes", [])
            if not final_workflow:
                raise ValueError("Final workflow is missing in state.")

            # Ensure the initial workflow exists.
            if not state.get("initial_workflow"):
                # logger.warning("Initial workflow missing; creating default initial_workflow.")
                state["initial_workflow"] = {
                    "subtasks": state.get("subtask_sequence", []),
                    "description": state.get("task", ""),
                    "steps": [{"step": step.get("node_id", ""), "description": ""} for step in state.get("plan", [])]
                }

                
            for key in ["task", "initial_workflow", "plan"]:
                if key not in state or not state[key]:
                    raise ValueError(f"Missing required state key: {key}")

            prompt = self.template_renderer.render_prompt(
                "map_workflow_edges.jinja2",
                task=state["task"],
                initial_workflow=state["initial_workflow"],
                plan=state["plan"],
                final_workflow=final_workflow
            )
            if not prompt:
                raise ValueError("Generated mapping prompt is empty.")
            # logger.info("Mapping prompt generated successfully.")

            workflow_json = self.ai_service.ask_ai(prompt, context="Return valid JSON")
            if not workflow_json:
                raise ValueError("AI returned an empty response for workflow mapping.")
            if isinstance(workflow_json, str):
                mapped_workflow = json.loads(workflow_json)
            else:
                mapped_workflow = workflow_json
            if "main" not in mapped_workflow:
                mapped_workflow = {"main": mapped_workflow}
            if not all(k in mapped_workflow["main"] for k in ["state", "nodes", "edges"]):
                raise ValueError("Mapped workflow is missing required keys (state, nodes, edges).")
            mapped_workflow["main"]["state"]["mainstate"] = "GraphState"
            state["final_workflow"] = mapped_workflow
            state["missing_nodes"] = missing_nodes
            # logger.info("Workflow edges mapped and final workflow updated successfully.")
            return state
        except Exception as e:
            # logger.error(f"Workflow mapping failed: {e}")
            raise

    def execute_step(self, state: AgentState) -> AgentState:
        """
        Execute the current step in the workflow by generating a partial workflow from the plan,
        updating the agent state with the latest step execution, and validating the process.

        @Feature: Agent State Management and Workflow Planning
        @Scenario: Execute a workflow step and update the agent state accurately

        Args:
            state (AgentState): The current agent state.

        Returns:
            AgentState: The updated state with an incremented 'current_step', updated 'final_workflow',
                        and 'workflow_valid' flag.

        Raises:
            RuntimeError: If generating the partial workflow fails.
        """
        try:
            current_step = state.get("current_step", 0)
            partial_plan = state.get("plan", [])[:current_step + 1]
            partial_workflow = self.generate_workflow_from_plan(state, plan=partial_plan)
            if not partial_workflow:
                state["workflow_valid"] = False
                return state
            state["current_step"] = current_step + 1
            state["workflow_valid"] = True
            state["final_workflow"] = partial_workflow
            # logger.info(f"Executed workflow step {current_step + 1} successfully.")
            return state
        except Exception as e:
            # logger.error(f"Error executing workflow step: {e}")
            raise RuntimeError("Workflow step execution failed.") from e

    def finalize(self, state: AgentState) -> AgentState:
        """
        Finalize the workflow by mapping workflow edges and formatting the final workflow JSON.
        This function preserves missing node data, validates the final structure against the expected schema,
        and logs the final output.

        @Feature: Agent State Management and Workflow Planning
        @Scenario: Finalize workflow by mapping edges and ensuring schema compliance

        Args:
            state (AgentState): The current agent state.

        Returns:
            AgentState: The updated state with a finalized and formatted workflow.

        Raises:
            RuntimeError: If finalization fails due to missing workflow data or mapping errors.
        """
        try:
            # print(f"\nFinalizing workflow with state: {state}\n")
            missing_nodes = state.get("missing_nodes", [])
            state = self.map_workflow_edges(state)
            final_workflow = state.get("final_workflow")
            print(f"\nFinal workflow after mapping Finalize: {final_workflow}\n")
            # if not final_workflow or "main" not in final_workflow:
            #     raise ValueError("Final workflow structure is invalid after mapping.")
            # formatted_workflow = {
            #     "state": final_workflow["main"].get("state", {}),
            #     "nodes": final_workflow["main"].get("nodes", []),
            #     "edges": final_workflow["main"].get("edges", [])
            # }
            # state["final_workflow"] = formatted_workflow
            # state["missing_nodes"] = missing_nodes
            # logger.info("Workflow finalized successfully.")
            # print("Final Workflow JSON:")
            # print(json.dumps(formatted_workflow, indent=2))
            return state
        except Exception as e:
            # logger.error(f"Finalization failed: {e}")
            raise RuntimeError("Workflow finalization failed.") from e

    def finalize_missing(self, state: AgentState):
        """Finalizes the workflow by mapping edges and saving the final workflow."""

        # Generate the final workflow
        missing_nodes = state["missing_nodes"]

        # Print missing nodes
        print("Missing_nodes:")
        print(missing_nodes)
        
        return state
    
