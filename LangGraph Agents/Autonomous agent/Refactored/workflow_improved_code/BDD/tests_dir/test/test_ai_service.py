import os
import re
import json
import pytest

from src.ai_service import AIService


class DummyResponse:
    def __init__(self, content):
        self.content = content


class DummyLLM:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    def invoke(self, messages):
        if self._exc:
            raise self._exc
        return self._response


def test_init_with_missing_model_env(monkeypatch):
    monkeypatch.delenv('MODEL_USED', raising=False)
    with pytest.raises(EnvironmentError) as exc_info:
        AIService(model=None)
    assert "Environment variable 'MODEL_USED' must be set" in str(exc_info.value)


def test_init_with_explicit_model(monkeypatch):
    svc = AIService(model='test-model', temperature=0.5)
    assert svc.llm is not None


@pytest.mark.parametrize('prompt,context', [('', 'ctx'), ('   ', 'ctx'), ('p', ''), ('p', '   ')])
def test_ask_ai_invalid_inputs(prompt, context):
    svc = AIService(model='m')
    with pytest.raises(ValueError):
        svc.ask_ai(prompt, context)


def test_ask_ai_llm_exception(monkeypatch):
    svc = AIService(model='m')
    svc.llm = DummyLLM(exc=Exception("fail"))
    with pytest.raises(RuntimeError) as exc_info:
        svc.ask_ai('p', 'c')
    assert "LLM invocation failed" in str(exc_info.value)


def test_ask_ai_missing_content_attr(monkeypatch):
    class NoContent:
        pass

    svc = AIService(model='m')
    svc.llm = DummyLLM(response=NoContent())
    with pytest.raises(RuntimeError) as exc_info:
        svc.ask_ai('p', 'c')
    assert "Invalid LLM response received" in str(exc_info.value)


def test_ask_ai_no_json_found(monkeypatch):
    svc = AIService(model='m')
    svc.llm = DummyLLM(response=DummyResponse(content='no json here'))
    with pytest.raises(RuntimeError) as exc_info:
        svc.ask_ai('p', 'c')
    assert "Failed to extract JSON" in str(exc_info.value)


def test_ask_ai_invalid_json(monkeypatch):
    bad_json = '{invalid: json}'
    svc = AIService(model='m')
    svc.llm = DummyLLM(response=DummyResponse(content=f'prefix {bad_json} suffix'))
    with pytest.raises(RuntimeError) as exc_info:
        svc.ask_ai('p', 'c')
    assert "Extracted JSON is invalid" in str(exc_info.value)


def test_ask_ai_valid_json(monkeypatch):
    valid = {"key": "value", "num": 123}
    json_str = json.dumps(valid)
    content = f"some text {json_str} more text"

    svc = AIService(model='m')
    svc.llm = DummyLLM(response=DummyResponse(content=content))
    result = svc.ask_ai('p', 'c')
    parsed = json.loads(result)
    assert parsed == valid
