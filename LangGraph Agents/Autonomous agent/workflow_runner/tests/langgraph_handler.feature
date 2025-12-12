Feature: LanggraphHandler Code Generation

  Scenario: Generate dynamic wrapper functions from node files
    Given a temporary folder with a Python file "example.py" containing a function "test_func" that takes parameters "a" and "b"
    And a JSON configuration with an edge targeting "test_func" mapping "a" to "param_a" and "b" to "param_b"
    When I generate dynamic wrapper functions to the file "wrapper_output.py" using LanggraphHandler
    Then the file "wrapper_output.py" should contain a wrapper function for "test_func"

  Scenario: Generate GraphState file from JSON input
    Given a JSON workflow with nodes having inputs "test_input" and outputs "test_output"
    When I generate the GraphState file to "state_output.py" using LanggraphHandler
    Then the file "state_output.py" should define a "GraphState" class with dynamic fields "test_input" and "test_output"

  Scenario: Generate registry file from function and state files
    Given existing function file "wrapper_output.py" and state file "state_output.py"
    When I generate the registry file to "registry_output.py" using LanggraphHandler
    Then the file "registry_output.py" should contain registry definitions for functions and classes
