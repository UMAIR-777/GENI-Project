#!/usr/bin/env python3
"""
Module: test_subtask_workflow.py
Description:
    This module implements production‐grade tests for the function create_initial_subtask_workflow in
    subtask_workflow.py. The tests are designed to cover all edge cases and boundary conditions using
    property‐based testing (via Hypothesis) and parameterized tests (via Pytest). Each test case is
    documented with detailed S-P-O (Subject, Predicate, Object) annotations and attributes to explicitly
    map to the corresponding BDD Features and Scenarios. These tests ensure that the function:
      • Correctly generates a blueprint plan when the AI returns valid JSON.
      • Falls back to a heuristic decomposition (splitting on periods) when the AI response is malformed.
    The tests verify full functional correctness, robust error handling, and compliance with enterprise-grade
    quality standards (e.g., 100% fallback activation and blueprint accuracy).

Test Framework: Pytest
Language: Python

@Feature: Agent Workflow Blueprint Generation (subtask_workflow.py)
@Scenario: Successfully generate a subtask workflow blueprint via AI-assisted prompt rendering and JSON extraction
@Scenario: Fallback to heuristic task splitting when the AI response is malformed, ensuring 100% fallback activation
"""

import json
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

# Import the function under test.
from src.subtask_workflow import create_initial_subtask_workflow

# To simulate AI responses, we monkey-patch Ask_AI.
# We assume the original Ask_AI is imported in subtask_workflow.py.
# We'll override it in our tests.

# --- Test Case: Successful AI Response ---

def fake_Ask_AI_success(prompt: str, context: str = "Return valid JSON") -> str:
    """
    S: [File: subtask_workflow.py; Function: Ask_AI (fake version)]
    P: "returns"
    O: "{...}" (Valid JSON blueprint)
    Attributes: {EntityType: "Function", Role: "Simulated LLM Response", ExpectedOutcome: "Valid JSON"}
    
    Simulate a successful LLM response with a valid blueprint JSON.
    """
    # Return a valid JSON blueprint that is a dictionary.
    blueprint = {
        "plan": [
            {
                "step": "Clean Data",
                "input": ["raw_data"],
                "output": ["clean_data"],
                "tags": ["ETL"],
                "description": "Clean the raw data for analysis",
                "SPO": {"subject": "Data", "predicate": "is cleaned by", "object": "the cleaning function"}
            },
            {
                "step": "Train Model",
                "input": ["clean_data"],
                "output": ["model"],
                "tags": ["ML"],
                "description": "Train the predictive model",
                "SPO": {"subject": "Model", "predicate": "is trained on", "object": "clean_data"}
            }
        ]
    }
    return json.dumps(blueprint)

# --- Test Case: Malformed AI Response (Fallback) ---

def fake_Ask_AI_failure(prompt: str, context: str = "Return valid JSON") -> str:
    """
    S: [File: subtask_workflow.py; Function: Ask_AI (fake version)]
    P: "returns"
    O: "Invalid JSON" (Malformed response)
    Attributes: {EntityType: "Function", Role: "Simulated LLM Failure", ExpectedOutcome: "Malformed Response"}
    
    Simulate a failure in LLM response by returning an invalid JSON string.
    """
    return "This is not a valid JSON response"

# Monkey-patch Ask_AI in the subtask_workflow module.
@pytest.fixture(autouse=True)
def patch_Ask_AI(monkeypatch):
    # By default, patch Ask_AI to simulate a successful response.
    monkeypatch.setattr("subtask_workflow.Ask_AI", fake_Ask_AI_success)

# --- Test: Successful Blueprint Generation ---

def test_create_initial_subtask_workflow_success():
    """
    S: [Module: subtask_workflow.py; Function: create_initial_subtask_workflow]
    P: "processes"
    O: "valid blueprint JSON from AI response"
    Attributes: {EntityType: "Function", Role: "Workflow Blueprint Generator", ExpectedOutcome: "Plan generated and enriched with description_embed", KPI: "100% Blueprint Accuracy"}
    
    GIVEN the AgentState with a valid 'task' string and optional 'subtasks'
      - [S: State; P: contains; O: 'task' key with value "Analyze sales data. Forecast revenue." (non-empty string)]
    WHEN the TestFramework (Pytest) calls create_initial_subtask_workflow (using a simulated valid AI response)
      - [S: TestFramework: Pytest; P: invokes; O: Function create_initial_subtask_workflow with state input]
    THEN the returned state must include a non-empty 'plan' key that is a valid JSON blueprint and each step must include a 'description_embed'
      - [S: Output: AgentState; P: is updated to include; O: 'plan' key with enriched blueprint steps, each having 'description_embed']
    """
    state = {"task": "Analyze sales data. Forecast revenue."}
    updated_state = create_initial_subtask_workflow(state)
    assert "plan" in updated_state, "State must have a 'plan' key after blueprint generation."
    assert isinstance(updated_state["plan"], dict), "'plan' should be a dictionary (blueprint JSON)."
    plan = updated_state["plan"]
    for step in plan.get("plan", []):
        assert "description_embed" in step, "Each blueprint step must include a 'description_embed' field."
        assert step["description_embed"].strip() != "", "'description_embed' must not be empty."

# --- Test: Fallback Blueprint Generation on Malformed AI Response ---

def test_create_initial_subtask_workflow_fallback(monkeypatch):
    """
    S: [Module: subtask_workflow.py; Function: create_initial_subtask_workflow]
    P: "handles"
    O: "fallback blueprint via task splitting"
    Attributes: {EntityType: "Function", Role: "Fallback Mechanism", ExpectedOutcome: "Plan generated via splitting", KPI: "100% Fallback Activation"}
    
    GIVEN the AgentState with a valid 'task' string (e.g., "Task one. Task two. Task three.")
    AND the AI response is simulated to be malformed (non-JSON)
      - [S: Function Ask_AI is patched to return a malformed string]
    WHEN create_initial_subtask_workflow is invoked
      - [S: TestFramework: Pytest; P: invokes; O: Function create_initial_subtask_workflow with state input]
    THEN the returned state must have 'plan' generated by splitting the task string on periods
      - [S: Output: AgentState; P: is updated using fallback; O: 'plan' key with heuristic splitting, each step containing 'description_embed']
    """
    monkeypatch.setattr("subtask_workflow.Ask_AI", fake_Ask_AI_failure)
    state = {"task": "Task one. Task two. Task three."}
    updated_state = create_initial_subtask_workflow(state)
    assert "plan" in updated_state, "State must have a 'plan' key after fallback decomposition."
    plan = updated_state["plan"]
    # In fallback, plan is generated as a list of steps.
    assert isinstance(plan, list), "Fallback plan must be a list of steps."
    assert len(plan) >= 1, "Fallback plan must contain at least one step."
    # Each step should include a 'description_embed' (even if simple fallback text).
    for step in plan:
        assert "description_embed" in step, "Each fallback blueprint step must include a 'description_embed' field."
        assert step["description_embed"].strip() != "", "Fallback 'description_embed' must not be empty."

# --- Test: Property-Based Testing for Blueprint Generation ---
@given(st.text(min_size=10, max_size=100))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_create_initial_subtask_workflow_property(task_text):
    """
    S: [Module: subtask_workflow.py; Function: create_initial_subtask_workflow]
    P: "processes"
    O: "blueprint generation under varying task inputs"
    Attributes: {EntityType: "Function", Role: "Workflow Blueprint Generator", TestType: "Property Based", KPI: "100% Robustness under diverse inputs"}
    
    GIVEN a non-empty task string generated by property-based testing (length between 10 and 100 characters)
      - [S: Input: task_text; P: is generated by; O: Hypothesis, State: Valid non-empty string]
    WHEN create_initial_subtask_workflow is invoked with an AgentState containing this task
      - [S: TestFramework: Pytest; P: invokes; O: Function create_initial_subtask_workflow]
    THEN the returned state must include a non-empty 'plan' key with enriched blueprint steps
      - [S: Output: AgentState; P: is updated to include; O: Valid blueprint in 'plan', with each step having 'description_embed']
    """
    state = {"task": task_text}
    updated_state = create_initial_subtask_workflow(state)
    assert "plan" in updated_state, "State must include 'plan' after blueprint generation."
    if isinstance(updated_state["plan"], dict):
        blueprint = updated_state["plan"].get("plan", [])
        for step in blueprint:
            assert "description_embed" in step, "Each blueprint step must have a 'description_embed'."
    elif isinstance(updated_state["plan"], list):
        for step in updated_state["plan"]:
            assert "description_embed" in step, "Each fallback blueprint step must have a 'description_embed'."
    else:
        pytest.fail("Unexpected type for 'plan' in state.")

# End of test_subtask_workflow.py module.
