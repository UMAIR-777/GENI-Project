import os
from langchain_groq import ChatGroq
import pytest
import json
import time
import heapq
from pytest_bdd import scenarios, given, when, then, parsers
import logging

logger = logging.getLogger(__name__)
from src.Nodes.AI_Agent_Step_Node_v3 import (
    ConfigLoader,
    TemplateRenderer,
    JSONCleaner,
    JSONParser,
    MetricSelector,
    LLMInvoker,
    generate_eval_metrics,
    run_ai_step_node,
    ConfigError,
    JSONParseError,
    LLMInvocationError
)

# Scenarios
scenarios('/home/kaleem/Work_Repos/WF/ai-workflow-research-py/LangGraph Agents/Autonomous agent/Refactored/workflow_improved_code/src/Nodes/BDD/AI_Step_v3.feature')

# Given Steps
@given('the [Component: EnvLoader] has loaded [.env] variables')
def given_env_loader(monkeypatch, tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text('MODEL_USED=test-model')
    monkeypatch.setenv('DOTENV_PATH', str(env_path))
    monkeypatch.setenv('MODEL_USED', 'test-model')
    return str(env_path)

@given('the [Component: TemplateLoader] has loaded [Directory: templates]')
def given_template_loader(monkeypatch, tmp_path):
    dir_path = tmp_path / 'templates'
    dir_path.mkdir()
    tmpl = dir_path / 'eval_template.jinja2'
    tmpl.write_text('{{ Role }}')
    monkeypatch.setenv('TEMPLATE_DIR', str(dir_path))
    return str(dir_path)

@given('an LLM returns valid JSON metrics')
def given_llm_valid(monkeypatch):
    class DummyResponse:
        content = json.dumps({
            "metrics": [
                {"metric": "m1", "insight_score": 5},
                {"metric": "m2", "insight_score": 7}
            ]
        })
    monkeypatch.setattr(LLMInvoker, 'invoke', lambda self, msgs: DummyResponse())

# When Steps
@when('we call generate_eval_metrics with [Parameter: role="Tester"], [Parameter: task="MyTask"], [Parameter: user_request="Do X"], [Parameter: context="ctx"], [Parameter: top_n=2]')
def when_call_generate(given_env_loader, given_template_loader, given_llm_valid):
    return generate_eval_metrics(
        role='Tester', task='MyTask', user_request='Do X', context='ctx', top_n=2
    )

@when('the LLM returns malformed JSON')
def when_llm_malformed(monkeypatch):
    class BadResponse:
        content = '```json {invalid} ```'
    monkeypatch.setattr(LLMInvoker, 'invoke', lambda self, msgs: BadResponse().content)
    # return function to invoke
    return generate_eval_metrics

@when(parsers.parse('we select top_n={top_n:d} metrics from a large list of size {size:d}'))
def when_select_metrics(top_n, size):
    metrics = [{"metric": f"m{i}", "insight_score": i} for i in range(size)]
    return MetricSelector.select(metrics, top_n)

# Then Steps
@then('the result is [Function: list] with metrics ["m2", "m1"]')
def then_metrics_sorted(when_call_generate):
    assert when_call_generate == ['m2', 'm1']

@then('the [Component: ExceptionHandler] catches [Error: JSONParseError]')
def then_json_error(when_llm_malformed):
    with pytest.raises(JSONParseError):
        when_llm_malformed(
            role='Tester', task='MyTask', user_request='Do X', context='ctx', top_n=1
        )

@then('MetricSelector.select returns [Type: list] of length {top_n:d}')
def then_selector_length(when_select_metrics, top_n, size):
    result = when_select_metrics
    assert isinstance(result, list)
    assert len(result) == top_n

# Additional edge case tests
@pytest.mark.parametrize('invalid_top_n', [0, -1, 'a'])
def test_generate_invalid_top_n(given_env_loader, given_template_loader, given_llm_valid, invalid_top_n):
    with pytest.raises(ValueError):
        generate_eval_metrics(
            role='R', task='T', user_request='U', context='', top_n=invalid_top_n
        )

def test_missing_env_loader():
    with pytest.raises(ConfigError):
        ConfigLoader(env_path='nonexistent.env')

@pytest.mark.parametrize('content', [123, None])
def test_json_cleaner_invalid_type(content):
    with pytest.raises(JSONParseError):
        JSONCleaner.clean(content)

# Model based state transitions
@when('run_ai_step_node is invoked for [User: Developer]')
def when_run_ai(monkeypatch, given_env_loader, given_template_loader):
    # Mock ChatGroq.invoke to return simple content
    monkeypatch.setenv('MODEL_USED', 'test-model')
    monkeypatch.setenv('DOTENV_PATH', given_env_loader)
    monkeypatch.setattr(ChatGroq, 'invoke', lambda self, msgs: type('R', (), {'content': 'result'}))
    return run_ai_step_node(role='Developer', task='Test', user_request='Req')

@then('the output is [Type: str] "result"')
def then_run_ai_result(when_run_ai):
    assert when_run_ai == 'result'

@given(parsers.parse('a valid [Function: generate_eval_metrics] request with [Parameter: role="{role}"] and [Parameter: task="{task}"]'))
def given_valid_generate_eval_metrics_request(role, task, monkeypatch, given_env_loader, given_template_loader, given_llm_valid):
    # Setup environment and template loader
    _ = given_env_loader
    _ = given_template_loader
    _ = given_llm_valid
    return {'role': role, 'task': task}

@given(parsers.parse('the LLM returns a response with {malformed}'))
def given_llm_returns_response_with(malformed, monkeypatch):
    class BadResponse:
        content = malformed
    monkeypatch.setattr(LLMInvoker, 'invoke', lambda self, msgs: BadResponse())
    return BadResponse()

@given(parsers.parse('a metrics list of size [State: {size:d}]'))
def given_metrics_list_of_size(size):
    return [{"metric": f"m{i}", "insight_score": i} for i in range(size)]

@given(parsers.parse('the [.env] file is missing [Key: {key}]'))
def given_env_file_missing_key(key, tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text('')  # empty .env file
    return str(env_path)

@given(parsers.parse('the system is in [State: {state}]'))
def given_system_in_state(state):
    # Mock or set system state as needed
    return state

@when(parsers.parse('the [Component: LLMInvoker] experiences {network_failure}'))
def when_llm_invoker_experiences_network_failure(network_failure, monkeypatch):
    def mock_invoke(self, msgs):
        raise Exception("Simulated network failure")
    monkeypatch.setattr(LLMInvoker, 'invoke', mock_invoke)

@given('the network call to ChatGroq API is delayed or fails intermittently')
def given_network_call_delayed(monkeypatch):
    # Mock ChatGroq.invoke to simulate network delay or failure
    def mock_invoke(self, msgs):
        import random
        import time
        if random.choice([True, False]):
            time.sleep(2)  # simulate delay
            return type('R', (), {'content': 'delayed response'})
        else:
            raise Exception("Network failure")
    monkeypatch.setattr(ChatGroq, 'invoke', mock_invoke)
