# File Name: json_to_langgraph.py
# Purpose: Build async, event-driven LangGraph workflows from JSON
# Supports: interrupts, resume, subgraphs, AI Voice Bot lifecycle

from typing import Dict, Callable, Tuple, List, Optional
from langgraph.graph import StateGraph, START, END
from backend.utils import group_by_source_and_function, extract_nodes
from backend.function_registry import get_function_reference, get_class_reference

import json
from pathlib import Path

config_path = Path(r"C:\ai_voice_bot\backend\graph_Ai.json")
with open(config_path, "r", encoding="utf-8") as f:
    app_json = json.load(f)

print(app_json["ai_voice_bot"]["nodes"])


# ------------------------------------------------------------------
# Core Graph Builder
# ------------------------------------------------------------------

def build_graph_from_json(
    app_json: Dict,
) -> Tuple[StateGraph, Dict, List[str]]:
    """
    Builds a LangGraph StateGraph from JSON configuration.
    Returns:
        - workflow (StateGraph)
        - input_var_dict (dict)
        - interrupt_nodes (list)
    """

    first_key = list(app_json.keys())[0]
    current_app_json = app_json[first_key]

    input_var_dict: Dict = {}
    conditional_edges: List = []
    interrupt_nodes: List[str] = []

    # -------------------------------
    # State Resolution
    # -------------------------------
    state_cfg = current_app_json.get("state", {})

    def resolve_state(name):
        if name in (None, "None"):
            return None
        return get_class_reference(name)

    mainstate_ref = resolve_state(state_cfg.get("mainstate"))
    inputstate_ref = resolve_state(state_cfg.get("inputstate"))
    outputstate_ref = resolve_state(state_cfg.get("outputstate"))

    workflow = StateGraph(
        state_schema=mainstate_ref,
        input=inputstate_ref,
        output=outputstate_ref,
    )

    # -------------------------------
    # Node Registration
    # -------------------------------
    for node in current_app_json.get("nodes", []):

        node_id = node["id"]

        # Skip start/end pseudo nodes
        if node_id in ("__start__", "__end__"):
            continue

        # ---------------------------
        # Subgraph Node
        # ---------------------------
        if (
            isinstance(node.get("data"), dict)
            and "id" in node["data"]
            and "CompiledStateGraph" in node["data"]["id"]
        ):
            sub_json = app_json[node_id]
            sub_workflow, sub_inputs, sub_interrupts = build_graph_from_json(
                {node_id: sub_json}
            )
            workflow.add_node(node_id, sub_workflow.compile())
            input_var_dict.update(sub_inputs)
            interrupt_nodes.extend(sub_interrupts)
            continue

        # ---------------------------
        # Runnable Node
        # ---------------------------
        fn_name = node["data"].get("name")
        fn_ref = get_function_reference(fn_name)
        workflow.add_node(node_id, fn_ref)

        # Collect node inputs
        input_var_dict.update(node.get("inputs", {}))

        # Interrupt-aware node
        if node.get("interrupt_after") is True:
            interrupt_nodes.append(node_id)

    # -------------------------------
    # Edge Registration
    # -------------------------------
    for edge in current_app_json.get("edges", []):

        if edge.get("conditional"):
            conditional_edges.append(edge)
            continue

        source = edge["source"]
        target = edge["target"]

        # Normalize START / END
        if source == "__start__":
            workflow.add_edge(START, target)
        elif target == "__end__":
            workflow.add_edge(source, END)
        else:
            workflow.add_edge(source, target)

    # -------------------------------
    # Conditional Edges
    # -------------------------------
    if conditional_edges:
        grouped = group_by_source_and_function(conditional_edges)

        for (edge_source, edge_fn), edges in grouped.items():
            fn_ref = get_function_reference(edge_fn)

            if edges[0]["condition_type"] == "dict":
                condition_map = {
                    e["data"]: e["target"] for e in edges
                }
                workflow.add_conditional_edges(
                    edge_source, fn_ref, condition_map
                )

            elif edges[0]["condition_type"] == "list":
                targets = [e["target"] for e in edges]
                workflow.add_conditional_edges(
                    edge_source, fn_ref, targets
                )

    return workflow, input_var_dict, interrupt_nodes


# ------------------------------------------------------------------
# Public Builder API
# ------------------------------------------------------------------

def graph_builder(input_json: Dict):
    """
    Compiles the graph with interrupt support.
    Returns:
        app            -> Compiled graph
        input_dict     -> Required input variables
        node_order     -> Execution order (linear)
    """

    workflow, input_dict, interrupt_nodes = build_graph_from_json(input_json)

    app = workflow.compile(
        interrupt_after=interrupt_nodes
    )

    first_key = list(input_json.keys())[0]
    node_order = extract_nodes(input_json[first_key])

    return app, input_dict, node_order


# ------------------------------------------------------------------
# Async Resume Entry (for Webhooks)
# ------------------------------------------------------------------

def resume_graph(app, saved_state: dict, event_payload: dict):
    """
    Resume graph after webhook / user response.
    """
    saved_state.update(event_payload)
    return app.invoke(saved_state)
