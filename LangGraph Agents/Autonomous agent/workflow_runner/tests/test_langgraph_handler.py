import os
import json
import shutil
import tempfile
from behave import given, when, then
from langgraph_handler import LanggraphHandler

# This will be our global temporary directory for the tests.
@given('a temporary folder with a Python file "example.py" containing a function "test_func" that takes parameters "a" and "b"')
def step_create_temp_folder_with_python_file(context):
    # Create a temporary directory
    context.temp_dir = tempfile.mkdtemp()
    context.example_file = os.path.join(context.temp_dir, "example.py")
    # Write a simple Python function into example.py
    code = (
        "def test_func(a, b=2):\n"
        "    return a + b\n"
    )
    with open(context.example_file, "w") as f:
        f.write(code)

@given('a JSON configuration with an edge targeting "test_func" mapping "a" to "param_a" and "b" to "param_b"')
def step_create_json_config(context):
    # Create a minimal JSON config with one edge mapping for test_func
    context.json_config = {
        "main": {
            "edges": [
                {
                    "source": "__start__",
                    "target": "test_func",
                    "mapping": {"a": "param_a", "b": "param_b"}
                }
            ]
        }
    }

@when('I generate dynamic wrapper functions to the file "wrapper_output.py" using LanggraphHandler')
def step_generate_wrapper_functions(context):
    # Define the output path for the wrapper file inside our temporary directory.
    context.wrapper_file = os.path.join(context.temp_dir, "wrapper_output.py")
    # Call the method
    LanggraphHandler.generate_wrapper_functions_dynamic(
        folder_path=context.temp_dir,
        output_file_path=context.wrapper_file,
        config_json=context.json_config
    )

@then('the file "wrapper_output.py" should contain a wrapper function for "test_func"')
def step_check_wrapper_file(context):
    assert os.path.exists(context.wrapper_file), "Wrapper output file was not created."
    with open(context.wrapper_file, "r") as f:
        content = f.read()
    # Check that the generated code contains a call to getattr(module, 'test_func')
    assert "getattr(module, 'test_func')" in content, "Wrapper for 'test_func' not found in the output file."

# --- Steps for GraphState generation ---
@given('a JSON workflow with nodes having inputs "test_input" and outputs "test_output"')
def step_create_json_workflow(context):
    # Create a JSON workflow with one node having inputs and outputs.
    context.json_workflow = {
        "main": {
            "nodes": [
                {
                    "id": "node1",
                    "type": "runnable",
                    "inputs": {"test_input": "value"},
                    "output": {"test_output": ""}
                },
                # Including __start__ and __end__ to mimic a real workflow
                {"id": "__start__", "type": "schema", "data": "__start__"},
                {"id": "__end__", "type": "schema", "data": "__end__"}
            ]
        }
    }

@when('I generate the GraphState file to "state_output.py" using LanggraphHandler')
def step_generate_graph_state_file(context):
    context.state_file = os.path.join(context.temp_dir, "state_output.py")
    LanggraphHandler.generate_graph_state_file(
        json_data=context.json_workflow,
        output_file_path=context.state_file
    )

@then('the file "state_output.py" should define a "GraphState" class with dynamic fields "test_input" and "test_output"')
def step_check_state_file(context):
    assert os.path.exists(context.state_file), "State output file was not created."
    with open(context.state_file, "r") as f:
        content = f.read()
    assert "class GraphState(TypedDict):" in content, "GraphState class definition not found."
    assert "test_input: str" in content, "Dynamic input field 'test_input' not found."
    assert "test_output: str" in content, "Dynamic output field 'test_output' not found."

# --- Steps for Registry generation ---
@given('existing function file "wrapper_output.py" and state file "state_output.py"')
def step_check_existing_files(context):
    # These files should have been created by the previous scenarios.
    assert os.path.exists(context.wrapper_file), "Wrapper file does not exist for registry generation."
    assert os.path.exists(context.state_file), "State file does not exist for registry generation."

@when('I generate the registry file to "registry_output.py" using LanggraphHandler')
def step_generate_registry_file(context):
    context.registry_file = os.path.join(context.temp_dir, "registry_output.py")
    LanggraphHandler.generate_registry_from_file_paths(
        function_file_path=context.wrapper_file,
        class_file_path=context.state_file,
        output_file_path=context.registry_file
    )

@then('the file "registry_output.py" should contain registry definitions for functions and classes')
def step_check_registry_file(context):
    assert os.path.exists(context.registry_file), "Registry file was not created."
    with open(context.registry_file, "r") as f:
        content = f.read()
    assert "function_registry =" in content, "Function registry definition not found."
    assert "class_registry =" in content, "Class registry definition not found."

# --- Cleanup temporary directory after all scenarios ---
def after_all(context):
    if hasattr(context, "temp_dir") and os.path.exists(context.temp_dir):
        shutil.rmtree(context.temp_dir)
