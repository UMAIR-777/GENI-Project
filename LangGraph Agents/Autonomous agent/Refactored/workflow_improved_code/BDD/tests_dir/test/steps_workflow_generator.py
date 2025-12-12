from pytest_bdd import scenarios, given, when, then, parsers
import json
import pytest
from BDD.tests_dir.test.test_workflow_generator import make_generator

scenarios('../features/workflow_generator.feature')

@pytest.fixture
def context():
    return {}

@given(parsers.parse('the [Input:user_task] is "{user_task}" [Function:generate_workflow]'))
def user_task(context, user_task):
    context['user_task'] = user_task

@given(parsers.parse('the [Component:DatabaseManager] returns one similar workflow record [API:retrieve_similar_workflow]'))
def db_returns_similar(make_generator, context):
    gen, _, db = make_generator({'retrieve': [(None, None, type('Dummy', (), {'state': {}, 'nodes': [], 'edges': []})(), None)]})
    context['gen'] = gen
    context['db'] = db

@given(parsers.parse('the [Component:DatabaseManager] returns no similar workflow records [API:retrieve_similar_workflow]'))
def db_returns_none(make_generator, context):
    gen, _, db = make_generator({'retrieve': []})
    context['gen'] = gen
    context['db'] = db

@when(parsers.parse('the [Function:generate_workflow] processes the retrieval branch [FunctionComponent:retrieval_logic]'))
def process_retrieval(context):
    js, missing = context['gen'].generate_workflow(context['user_task'])
    context['result'] = (js, missing)

@when(parsers.parse('the [Function:generate_workflow] generates a new workflow [FunctionComponent:planning_logic]'))
def generate_new_workflow(context):
    js, missing = context['gen'].generate_workflow(context['user_task'])
    context['result'] = (js, missing)

@then(parsers.parse('it returns a JSON payload containing the existing workflow under key "main" [Concept:ResultSerialization]'))
def assert_existing_workflow(context):
    js, missing = context['result']
    data = json.loads(js)
    assert 'main' in data
    assert missing == []

@then(parsers.parse('it returns a JSON payload containing the new workflow [Concept:ResultSerialization]'))
def assert_new_workflow(context):
    js, missing = context['result']
    data = json.loads(js)
    assert 'nodes' in data or 'main' in data
    assert missing == []

@then(parsers.parse('the [State:missing_nodes] list is empty [State:missing_nodes]'))
def assert_no_missing_nodes(context):
    js, missing = context['result']
    assert missing == []

@then(parsers.parse('the workflow is saved successfully to the database [Component:DatabaseManager]'))
def assert_workflow_saved(context):
    db = context['db']
    # Check that save_workflow was called at least once
    assert any(call[0] == 'save' for call in db.calls)
