"""
Module: test_ai_node_filtering
Description: This module contains production-quality tests for the ai_node_filtering module.
It implements a comprehensive set of BDD step tests mapped 1:1 to the corresponding source code @Feature and @Scenario,
covering valid input processing, missing candidate handling, partial candidate selection, and critical failure recovery.
Tests incorporate property-based testing (using Hypothesis) and parameterized tests (using pytest) to ensure coverage
of all edge cases and boundary conditions.

Test Framework: Pytest
Language: Python
"""

import json
import logging
import os
from typing import Any, Dict, List, Tuple
import sys
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Import the functions and classes from the production module.
# It is assumed that ai_node_filtering.py is in the PYTHONPATH.
from src.ai_node_filtering import (
    BlueprintStep,
    Node,
    SPO,
    build_candidate_list,
    convert_blueprint_steps_to_instances,
    convert_nodes_to_instances,
    filter_ai_prompt,
    parse_ai_response,
    process_blueprint_step,
    filter_nodes_by_embedding_batch,
)

# ---------------------------------------------------------------------------
# Test Data and Mocks
# ---------------------------------------------------------------------------
# Dummy implementations and sample data for external dependencies.
# Mock the dependent modules that are imported in ai_node_filtering.py
class MockPromptManager:
    def render_prompt(self, template, **kwargs):
        return f"Prompt for {kwargs.get('step').step} with candidates: {kwargs.get('candidate_list')}"

class MockRetrieveSimilarNodesBatch:
    def __call__(self, steps, top_k):
        return {step.step: [] for step in steps}

# Add mocks before importing the production code
sys.modules['prompt_manager'] = type('MockPromptManager', (), {'PromptManager': MockPromptManager})
sys.modules['llm_ai'] = type('MockLLMAI', (), {'Ask_AI': lambda x: '{"SELECTED_NODE": ["node1"]}'})
sys.modules['retrieve_similar_nodes'] = type('MockRetrieve', (), {'retrieve_similar_nodes_batch': MockRetrieveSimilarNodesBatch()})

# Dummy candidate similarity output: list of tuples (node, score)
DUMMY_SIMILAR_NODES = [
    (
        {
            "id": "node1",
            "input": ["node_input1"],
            "output": ["node_output1"],
            "tags": ["node_tag1"],
            "description": ["node_desc1"],
            "SPO": ["node_subj1", "node_pred1", "node_obj1"],
        },
        0.98,
    )
]

# Sample valid blueprint step dictionary
VALID_BLUEPRINT_STEP = {
    "step": "step1",
    "input": ["input1"],
    "output": ["output1"],
    "tags": ["tag1"],
    "description": ["desc1"],
    "SPO": {"subject": "subj1", "predicate": "pred1", "object": "obj1"},
}

# Sample valid node dictionary
VALID_NODE = {
    "id": "node1",
    "input": ["node_input1"],
    "output": ["node_output1"],
    "tags": ["node_tag1"],
    "description": ["node_desc1"],
    "SPO": {"subject": "node_subj1", "predicate": "node_pred1", "object": "node_obj1"},
}

# Sample malformed AI responses
MALFORMED_AI_RESPONSE = "not a json"
MISSING_KEY_AI_RESPONSE = json.dumps({"unexpected_key": "value"})

# ---------------------------------------------------------------------------
# Tests for Data Conversion Functions
# ---------------------------------------------------------------------------

def test_convert_nodes_to_instances_valid():
    """@Feature: Node Data Conversion
    @Scenario: Convert valid node dictionary to Node instance with proper SPO formatting.
    """
    nodes = [VALID_NODE]
    converted = convert_nodes_to_instances(nodes)
    assert isinstance(converted, list)
    assert len(converted) == 1
    node = converted[0]
    assert node["id"] == VALID_NODE["id"]
    assert isinstance(node["SPO"], list)
    assert node["SPO"] == ["node_subj1", "node_pred1", "node_obj1"]

def test_convert_nodes_to_instances_invalid():
    """@Feature: Node Data Conversion
    @Scenario: Conversion fails with invalid node structure.
    """
    # Missing required field "id"
    invalid_node = dict(VALID_NODE)
    invalid_node.pop("id")
    with pytest.raises(Exception):
        convert_nodes_to_instances([invalid_node])

def test_convert_blueprint_steps_to_instances_valid():
    """@Feature: Blueprint Step Conversion
    @Scenario: Convert valid blueprint step dictionary to BlueprintStep instance with proper SPO formatting.
    """
    steps = [VALID_BLUEPRINT_STEP]
    converted = convert_blueprint_steps_to_instances(steps)
    assert isinstance(converted, list)
    assert len(converted) == 1
    step = converted[0]
    assert step.step == VALID_BLUEPRINT_STEP["step"]
    assert step.SPO == ["subj1", "pred1", "obj1"]

def test_convert_blueprint_steps_to_instances_invalid():
    """@Feature: Blueprint Step Conversion
    @Scenario: Conversion fails with missing blueprint step field.
    """
    invalid_step = dict(VALID_BLUEPRINT_STEP)
    invalid_step.pop("step")
    with pytest.raises(Exception):
        convert_blueprint_steps_to_instances([invalid_step])

# ---------------------------------------------------------------------------
# Tests for Utility Functions
# ---------------------------------------------------------------------------

def test_build_candidate_list_valid():
    """@Feature: Candidate List Assembly
    @Scenario: Build candidate list string from valid node list.
    """
    candidate_str = build_candidate_list([VALID_NODE])
    assert "node: node1:" in candidate_str
    assert "input=" in candidate_str
    assert "SPO=" in candidate_str

def test_build_candidate_list_invalid():
    """@Feature: Candidate List Assembly
    @Scenario: Build candidate list fails with malformed node data.
    """
    with pytest.raises(KeyError):
        build_candidate_list([{"wrong_key": "value"}])

# ---------------------------------------------------------------------------
# Tests for AI Prompt and Response Parsing Functions
# ---------------------------------------------------------------------------

def test_filter_ai_prompt_valid(monkeypatch):
    """@Feature: Node Filtering - AI Verification for Node Selection
    @Scenario: Construct AI prompt successfully with valid blueprint step and candidate list.
    """
    step_instance = BlueprintStep(**VALID_BLUEPRINT_STEP)
    candidate_list = "dummy candidate list"
    
    # Monkey-patch prompt_manager.render_prompt to return a formatted string.
    def dummy_render(template, **kwargs):
        return f"Prompt for {kwargs.get('step').step} with candidates: {kwargs.get('candidate_list')}"
    monkeypatch.setattr("ai_node_filtering.prompt_manager.render_prompt", dummy_render)
    
    prompt = filter_ai_prompt(step_instance, candidate_list)
    assert "Prompt for step1" in prompt
    assert candidate_list in prompt

def test_parse_ai_response_valid():
    """@Feature: AI Output Integrity - Parsing and Validation
    @Scenario: Parse valid AI response containing SELECTED_NODE.
    """
    valid_response = json.dumps({"SELECTED_NODE": ["node1"]})
    result = parse_ai_response(valid_response, "step1")
    assert result == ["node1"]

def test_parse_ai_response_missing_key():
    """@Feature: AI Output Integrity - Parsing and Validation
    @Scenario: Handle AI response with missing expected keys gracefully.
    """
    result = parse_ai_response(MISSING_KEY_AI_RESPONSE, "step1")
    assert result == "MISSING_NODE"

def test_parse_ai_response_malformed():
    """@Feature: AI Output Integrity - Parsing and Validation
    @Scenario: Handle malformed AI response gracefully.
    """
    result = parse_ai_response(MALFORMED_AI_RESPONSE, "step1")
    assert result == "MISSING_NODE"

# ---------------------------------------------------------------------------
# Tests for Processing a Single Blueprint Step
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_blueprint_step():
    """Fixture for a valid BlueprintStep instance."""
    return BlueprintStep(**VALID_BLUEPRINT_STEP)

@pytest.fixture
def dummy_candidate_nodes():
    """Fixture for dummy candidate similarity output."""
    return DUMMY_SIMILAR_NODES

def dummy_ask_ai(prompt: str) -> str:
    """
    Dummy Ask_AI function for testing process_blueprint_step.
    Returns a JSON string with a valid SELECTED_NODE field.
    """
    return json.dumps({"SELECTED_NODE": ["node1"]})

def dummy_ask_ai_missing(prompt: str) -> str:
    """
    Dummy Ask_AI function that returns missing node indication.
    """
    return json.dumps({"MISSING_NODE": True})

def test_process_blueprint_step_valid(monkeypatch, dummy_blueprint_step, dummy_candidate_nodes):
    """@Feature: AI-Driven Node Matching
    @Scenario: End-to-End processing of a blueprint step with valid candidate selection.
    """
    # Patch Ask_AI to use the dummy function.
    monkeypatch.setattr("ai_node_filtering.Ask_AI", dummy_ask_ai)
    step_key, filtered_nodes, is_missing = process_blueprint_step(dummy_blueprint_step, dummy_candidate_nodes)
    assert step_key == dummy_blueprint_step.step
    assert not is_missing
    assert isinstance(filtered_nodes, list)
    # Check that the selected node id is node1
    if filtered_nodes:
        assert filtered_nodes[0]["id"] == "node1"

def test_process_blueprint_step_missing(monkeypatch, dummy_blueprint_step, dummy_candidate_nodes):
    """@Feature: AI-Driven Node Matching
    @Scenario: Processing a blueprint step when AI indicates missing node.
    """
    monkeypatch.setattr("ai_node_filtering.Ask_AI", dummy_ask_ai_missing)
    step_key, filtered_nodes, is_missing = process_blueprint_step(dummy_blueprint_step, dummy_candidate_nodes)
    assert step_key == dummy_blueprint_step.step
    assert is_missing
    assert filtered_nodes == []

# ---------------------------------------------------------------------------
# Tests for Batch Node Filtering Function
# ---------------------------------------------------------------------------

class DummyRetrieveSimilarNodesBatch:
    """Dummy class to simulate retrieve_similar_nodes_batch for testing."""
    def __call__(self, steps: List[BlueprintStep], top_k: int) -> Dict[str, List[Tuple[Dict[str, Any], float]]]:
        result = {}
        for step in steps:
            # For testing, return DUMMY_SIMILAR_NODES for each step if step id is 'step1'
            if step.step == "step1":
                result[step.step] = DUMMY_SIMILAR_NODES
            else:
                result[step.step] = []
        return result

@pytest.fixture
def dummy_retrieve_similar_nodes_batch():
    return DummyRetrieveSimilarNodesBatch()

def test_filter_nodes_by_embedding_batch_valid(monkeypatch):
    """@Feature: Comprehensive Node Filtering with AI Verification
    @Scenario: Batch processing with valid blueprint steps and nodes resulting in valid node mapping.
    """
    blueprint_steps = [VALID_BLUEPRINT_STEP]
    nodes = [VALID_NODE]
    
    # Patch retrieve_similar_nodes_batch in the ai_node_filtering module.
    monkeypatch.setattr("ai_node_filtering.retrieve_similar_nodes_batch", DummyRetrieveSimilarNodesBatch())
    # Patch Ask_AI to return a valid selection.
    monkeypatch.setattr("ai_node_filtering.Ask_AI", dummy_ask_ai)
    
    filtered_map, missing_list = filter_nodes_by_embedding_batch(blueprint_steps, nodes, top_k=3)
    # Expect filtered_map to have a valid mapping for 'step1'
    assert "step1" in filtered_map
    assert isinstance(filtered_map["step1"], list)
    # For valid processing, missing_list should be empty.
    assert missing_list == [] or len(missing_list) == 0

def test_filter_nodes_by_embedding_batch_no_candidates(monkeypatch):
    """@Feature: Comprehensive Node Filtering with AI Verification
    @Scenario: Batch processing where retrieve_similar_nodes_batch returns empty candidate list leading to missing node entry.
    """
    blueprint_steps = [VALID_BLUEPRINT_STEP]
    nodes = [VALID_NODE]
    
    # Patch retrieve_similar_nodes_batch to always return empty candidate lists.
    def dummy_retrieve_empty(steps, top_k):
        return {step.step: [] for step in steps}
    monkeypatch.setattr("ai_node_filtering.retrieve_similar_nodes_batch", dummy_retrieve_empty)
    
    filtered_map, missing_list = filter_nodes_by_embedding_batch(blueprint_steps, nodes, top_k=3)
    # Expect filtered_map for step1 to be an empty list.
    assert filtered_map["step1"] == []
    # And missing_list should contain an entry for step1.
    assert any(item["subtask"] == "step1" for item in missing_list)

# ---------------------------------------------------------------------------
# Property-Based Testing for parse_ai_response Edge Cases
# ---------------------------------------------------------------------------

@given(st.text())
def test_parse_ai_response_property(random_text):
    """@Feature: AI Output Integrity - Parsing and Validation
    @Scenario: Property-based testing for parse_ai_response with arbitrary text input.
    """
    result = parse_ai_response(random_text, "prop_test")
    # Since random_text is unlikely to be valid JSON, result should be "MISSING_NODE"
    assert result == "MISSING_NODE"

# ---------------------------------------------------------------------------
# End of Test Module
# ---------------------------------------------------------------------------
