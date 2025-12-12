from venv import logger
import pytest
import json
import logging
import time
from hypothesis import given, strategies as st
from typing import Any, Dict, List
import sys
from pathlib import Path
# Ensure src in path
src_path = Path(__file__).parent.parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
from src.workflow_planner import WorkflowPlanner, WorkflowError, AgentState

# --- Mocks & Utilities ---
class DummyRenderer:
    def render_prompt(self, template: str, **kwargs) -> str:
        return f"PROMPT[{template}]" + json.dumps(kwargs)

class DummyAIService:
    def __init__(self, response: str):
        self.response = response
    def ask_ai(self, prompt: str, context: str) -> str:
        return self.response

class DummyNodeService:
    def __init__(self, outcome: Any):
        self.outcome = outcome
    def filter_nodes_by_embedding_batch(
        self, state: AgentState, plan: List[Dict[str, Any]], available: List[Any]
    ) -> Any:
        return self.outcome

@pytest.fixture(scope="session")
def base_state() -> AgentState:
    """
    Provides a fresh, empty AgentState.
    """
    return {}

@pytest.fixture(scope="session")
def planner() -> WorkflowPlanner:
    """
    Constructs a WorkflowPlanner with default dummy services.
    """
    return WorkflowPlanner(
        template_renderer=DummyRenderer(),
        ai_service=DummyAIService('{}'),
        node_service=DummyNodeService(({}, [])),
        available_nodes=[]
    )

# --- Feature: State Initialization ---

@pytest.mark.parametrize("invalid_input", [None, 123, "string", [1,2,3]])
def test_initialize_state_invalid_type(planner, invalid_input):
    """
    @Feature {State Initialization}
    @Scenario {reject invalid state types}
    """
    with pytest.raises(ValueError, match="Agent state must be a dictionary."):
        planner.initialize_state(invalid_input)  # type: ignore

def test_initialize_state_defaults(planner):
    """
    @Feature {State Initialization}
    @Scenario {populate default state keys}
    """
    state = planner.initialize_state({})
    expected_keys = [
        'task','allowed_nodes','available_nodes','subtasks','subtask_sequence',
        'plan','context','current_step','workflow_valid','final_workflow',
        'evaluation','replan_attempts','initial_workflow','missing_nodes','missing_node_error'
    ]
    for key in expected_keys:
        assert key in state

@given(extra=st.dictionaries(st.text(min_size=1), st.one_of(st.integers(), st.text(), st.lists(st.text())), max_size=3))
def test_initialize_state_preserves_existing(planner, extra):
    """
    @Feature {State Initialization}
    @Scenario {preserve existing state values}
    """
    state = {'current_step': 5}
    state.update(extra)
    result = planner.initialize_state(state)
    assert result['current_step'] == 5
    for k in extra:
        assert result[k] == extra[k]

# --- Feature: Task Decomposition ---

def test_decompose_task_missing_task(planner, base_state):
    """
    @Feature {Task Decomposition}
    @Scenario {error on missing or empty task}
    """
    with pytest.raises(ValueError):
        planner.decompose_task(base_state)

@given(task=st.text(min_size=2)
       .map(lambda x: f"A.{x}.C")  # Ensure valid task format with dots
       .filter(lambda x: len(x.split('.')) >= 3))  # Ensure at least 3 subtasks
def test_decompose_task_fallback_and_success(planner, base_state, task):
    """
    @Feature {Task Decomposition}
    @Scenario {fallback heuristic on invalid AI response}
    @Scenario {parse valid AI JSON into subtasks}
    """
    # Prepare state
    base_state['task'] = task
    
    # Test fallback path
    planner.ai_service = DummyAIService('invalid json')
    state_fb = planner.decompose_task(base_state.copy())
    subtasks_fb = [s.strip() for s in task.split('.') if s.strip()]
    assert state_fb['subtasks'] == subtasks_fb
    assert state_fb['subtask_sequence'] == subtasks_fb
    
    # Test success path
    subtasks = [s.strip() for s in task.split('.') if s.strip()]
    response = json.dumps({
        'subtasks': subtasks,
        'sequence': subtasks
    })
    planner.ai_service = DummyAIService(response)
    state_ok = planner.decompose_task(base_state.copy())
    assert state_ok['subtasks'] == subtasks

# --- Feature: Blueprint Generation ---
def test_create_initial_subtask_workflow_error(planner, base_state):
    """
    @Feature {Blueprint Generation}
    @Scenario {error on missing task}
    """
    # Remove task or set it to empty to trigger error
    base_state['task'] = ''
    base_state['subtasks'] = []
    with pytest.raises(ValueError, match="Agent state must include a non-empty 'task' string."):
        planner.create_initial_subtask_workflow(base_state)

@given(subtasks=st.lists(st.text(min_size=1), min_size=1))
def test_create_initial_subtask_workflow_fallback_and_success(planner, base_state, subtasks):
    """
    @Feature {Blueprint Generation}
    @Scenario {fallback blueprint on invalid AI JSON}
    @Scenario {build plan from AI JSON dict}
    """
    base_state.update({'task':'T','subtasks':subtasks})
    # Fallback path
    planner.ai_service = DummyAIService('not json')
    state_fb = planner.create_initial_subtask_workflow(base_state.copy())
    assert all('fallback' in step['tags'] for step in state_fb['plan'])
    
    # Success path
    blueprint = [{
        'step': s,
        'input': ['i'],
        'output': ['o'],
        'tags': ['t'],
        'description': 'd',
        'SPO': ['s', 'p', 'o']  # Changed to list format
    } for s in subtasks]
    response = json.dumps(blueprint)
    planner.ai_service = DummyAIService(response)
    state_ok = planner.create_initial_subtask_workflow(base_state.copy())
    for orig, built in zip(blueprint, state_ok['plan']):
        assert built['step'] == orig['step']
        assert built['SPO'] == orig['SPO']  # Compare list formats

# --- Feature: Plan Batch Generation ---
def test_generate_plan_batch_node_error(planner):
    """
    @Feature {Plan Batch Generation}
    @Scenario {handle node filtering error}
    """
    state = {
        'task': 'X',
        'subtasks': ['X'],
        'plan': [{'step': 'X', 'description': 'test'}],
        'subtask_sequence': ['X'],
        'available_nodes': [],
        'missing_nodes': []
    }
    planner.node_service = DummyNodeService(None)  # Return None to trigger error
    result = planner.generate_plan_batch(state)
    assert result['missing_node_error'] is True

def test_generate_plan_batch_success(planner):
    """
    @Feature {Plan Batch Generation}
    @Scenario {map nodes into plan entries}
    """
    # Setup initial state with complete metadata
    state = {
        'task': 'Content Creation Pipeline',
        'subtasks': ['Video Transcript Generation'],
        'subtask_sequence': ['Video Transcript Generation'],
        'plan': [{
            'step': 'Video Transcript Generation',
            'description': 'Generate transcript from video',
            'input': ['video_file'],
            'output': ['transcript_text'],
            'tags': ['transcription', 'video processing'],
            'SPO': {
                'subject': 'transcriber',
                'predicate': 'generates',
                'object': 'transcript'
            }
        }],
        'available_nodes': ['Get_Youtube_Transcript']
    }

    # Setup node service mock with matching metadata structure
    map_entries = {
        'Video Transcript Generation': [{
            'id': 'Get_Youtube_Transcript',
            'input': ['youtube_url', 'video_url'],
            'output': ['transcript'],
            'tags': ['YouTube', 'Transcription'],
            'description': 'Retrieves transcript from YouTube video',
            'SPO': {
                'subject': 'YouTube transcriber',
                'predicate': 'extracts',
                'object': 'transcript'
            }
        }]
    }

    # Configure mock service
    planner.node_service = DummyNodeService((map_entries, []))

    # Mock the AI service to return proper blueprint
    blueprint_response = json.dumps([{
        'step': 'Video Transcript Generation',
        'description': 'Generate transcript from video',
        'input': ['video_file'],
        'output': ['transcript_text'],
        'tags': ['transcription', 'video processing'],
        'SPO': {
            'subject': 'transcriber',
            'predicate': 'generates',
            'object': 'transcript'
        }
    }])
    planner.ai_service = DummyAIService(blueprint_response)

    # Execute test
    result = planner.generate_plan_batch(state)

    # Verify results with complete assertions
    assert result is not None, "Result should not be None"
    assert 'plan' in result, "Result should contain plan"
    assert isinstance(result['plan'], list), "Plan should be a list"
    assert len(result['plan']) > 0, "Plan should not be empty"
    
    expected_plan_entry = {
        'node_id': 'Get_Youtube_Transcript',
        'inputs': ['youtube_url', 'video_url'],
        'output': ['transcript'],
        'step': 'Video Transcript Generation'
    }
    
    assert result['plan'][0] == expected_plan_entry, "Plan entry should match expected structure"

def test_generate_plan_batch_invalid_subtask_mapping(planner):
    """Test plan generation with invalid subtask mapping"""
    # Match BDD failure scenario
    state = {
        'task': 'Test Task',
        'subtasks': ['T'], 
        'plan': [{
            'step': 'T'
        }],
        'available_nodes': [],
        'missing_nodes': []
    }
    
    # Mock returns error as specified in BDD
    planner.node_service = DummyNodeService("error")
    
    result = planner.generate_plan_batch(state)
    
    # Match BDD assertions
    assert result['missing_node_error'] is True
    assert result['plan'] == state['plan']  # Plan remains unchanged

def test_generate_plan_batch_empty_subtasks(planner):
    """Test plan generation with empty subtasks"""
    state = {
        'task': 'Test Task',
        'subtasks': [],
        'plan': [],
        'subtask_sequence': [],
        'available_nodes': [],
        'missing_nodes': []
    }
    planner.node_service = DummyNodeService(({}, []))  # Empty node mapping
    result = planner.generate_plan_batch(state)
    assert isinstance(result['plan'], list)
    assert len(result['plan']) == 0

# --- Feature: Step Execution ---

def test_execute_step_empty_plan(planner, base_state):
    """
    @Feature {Step Execution}
    @Scenario {handle empty plan gracefully}
    """
    base_state['plan'] = []
    result = planner.execute_step(base_state.copy())
    assert result['workflow_valid'] is False

def test_execute_step_increments_state(planner):
    """
    @Feature {Step Execution}
    @Scenario {increase step and validate workflow}
    """
    state = {'plan':[{'node_id':'__start__','inputs':{},'output':{}},{'node_id':'__end__','inputs':{},'output':{}}],'current_step':0}
    result = planner.execute_step(state.copy())
    assert result['current_step'] == 1 and result['workflow_valid'] is True

# --- Feature: Workflow Edge Mapping ---
def map_workflow_edges(self, state: AgentState) -> AgentState:
    """
    @Feature {Workflow Edge Mapping}
    @Scenario {update state on valid AI mapping}
    """
    if 'final_workflow' not in state or not state['final_workflow']:
        logger.error("map_workflow_edges: missing final_workflow")
        raise ValueError("Final workflow is missing in state.")
        
    # Ensure required state components exist
    if not all(key in state for key in ['task', 'initial_workflow', 'plan']):
        logger.error("map_workflow_edges: missing prerequisites")
        raise ValueError("Missing required state for mapping.")
        
    # Ensure final_workflow has main section
    if 'main' not in state['final_workflow']:
        state['final_workflow']['main'] = {'nodes': [], 'edges': []}

    try:
        prompt = self.template_renderer.render_prompt(
            'map_workflow_edges.jinja2',
            task=state['task'],
            initial_workflow=state['initial_workflow'],
            plan=state['plan'],
            final_workflow=state['final_workflow']
        )
        
        response = self.ai_service.ask_ai(prompt, context='Return valid JSON')
        mapped = json.loads(response)
        
        # Ensure proper structure
        if 'main' not in mapped:
            mapped = {'main': mapped}
            
        mapped['main'].setdefault('state', {})['mainstate'] = 'GraphState'
        state['final_workflow'] = mapped
        
        return state
        
    except Exception as e:
        logger.error(f"map_workflow_edges failed: {str(e)}")
        raise

def test_map_workflow_edges_missing(planner, base_state):
    """
    @Feature {Workflow Edge Mapping}
    @Scenario {error on missing final_workflow}
    """
    with pytest.raises(ValueError):
        planner.map_workflow_edges(base_state)

@pytest.fixture
def mapped_state() -> AgentState:
    return {'task':'T','initial_workflow':{},'plan':[{}],'final_workflow':{}}  

def test_map_workflow_edges_success(planner, mapped_state):
    """
    @Feature {Workflow Edge Mapping}
    @Scenario {update state on valid AI mapping}
    """
    # Initialize state with required fields
    mapped_state.update({
        'task': 'Test Task',
        'initial_workflow': {'steps': [{'step': 'A'}]},
        'plan': [{'node_id': 'A'}],
        'final_workflow': {'main': {'nodes': [], 'edges': []}}
    })
    
    resp = json.dumps({
        'main': {
            'state': {},
            'nodes': [],
            'edges': [{'source': 'A', 'target': 'B'}]
        }
    })
    planner.ai_service = DummyAIService(resp)
    result = planner.map_workflow_edges(mapped_state.copy())
    
    assert 'main' in result['final_workflow']
    assert 'edges' in result['final_workflow']['main']
    assert result['final_workflow']['main']['edges'][0] == {'source': 'A', 'target': 'B'}

# --- Feature: Finalization ---

def test_finalize_missing_logs(planner, base_state, caplog):
    """
    @Feature {Finalize Missing Nodes}
    @Scenario {log missing nodes}
    """
    caplog.set_level(logging.INFO)
    state = {'missing_nodes':['X']}
    result = planner.finalize_missing(state.copy())
    assert 'Missing nodes at finalize_missing' in caplog.text

@pytest.fixture(scope="session")
def finalize_state() -> AgentState:
    return {
        'task': 'Test Task',
        'initial_workflow': {'steps': [{'step': 'A'}]},
        'plan': [{'node_id': 'A'}],
        'final_workflow': {'main': {'nodes': [], 'edges': []}}
    }

def test_finalize_calls_map(planner, finalize_state):
    """
    @Feature {Workflow Edge Mapping}
    @Scenario {update state on valid AI mapping}
    """
    resp = json.dumps({
        'main': {
            'state': {},
            'nodes': [],
            'edges': [{'source': 'A', 'target': 'B'}]
        }
    })
    planner.ai_service = DummyAIService(resp)
    result = planner.finalize(finalize_state.copy())
    assert 'main' in result['final_workflow']
    assert 'edges' in result['final_workflow']['main']

# --- Integration Model-Based Test ---

def test_full_workflow_pipeline(planner, caplog):
    caplog.set_level(logging.INFO)
    state = planner.initialize_state({})
    state['task'] = 'X.Y'
    
    # Mock AI responses
    planner.ai_service = DummyAIService(json.dumps({
        'subtasks': ['X', 'Y'],
        'sequence': ['X', 'Y']
    }))
    
    state = planner.decompose_task(state)
    
    # Mock blueprint
    blueprint = [{
        'step': 'X',
        'input': ['i'],
        'output': ['o'],
        'tags': ['t'],
        'description': 'd',
        'SPO': {'subject': 's', 'predicate': 'p', 'object': 'o'}
    }]
    planner.ai_service = DummyAIService(json.dumps(blueprint))
    state = planner.create_initial_subtask_workflow(state)
    
    # Mock node mapping
    node_map = {
        'X': [{'id': 'nid', 'input': ['in'], 'output': ['out']}],
        'Y': [{'id': 'nid2', 'input': ['in2'], 'output': ['out2']}]
    }
    planner.node_service = DummyNodeService((node_map, []))
    state = planner.generate_plan_batch(state)
    
    # Execute and finalize
    state = planner.execute_step(state)
    planner.ai_service = DummyAIService(json.dumps({
        'main': {
            'state': {},
            'edges': [{'source': 'nid', 'target': 'nid2'}]
        }
    }))
    final = planner.finalize(state)
    assert final['final_workflow']['main']['edges'][0] == {
        'source': 'nid',
        'target': 'nid2'
    }