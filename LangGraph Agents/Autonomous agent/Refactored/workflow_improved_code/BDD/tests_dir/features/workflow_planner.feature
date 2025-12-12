Feature: WorkflowPlanner Core Operations for Robust Workflow Generation [KPI: 100% Functional Coverage, ≥ 90% Code Coverage]

  As an [User: AIEngineer]
  I want the [Component: WorkflowPlanner] to correctly execute each workflow phase
  so that automated workflows are reliable, performant, and handle all edge cases.

  Background:
    Given a [Component: TemplateRenderer] mock is provided
    And a [Component: AIService] mock is provided
    And a [Component: NodeService] mock is provided
    And a [Class: WorkflowPlanner] instance is initialized with the mocks

  @initialize_state @validation
  Scenario Outline: [Function: initialize_state] rejects invalid [Entity: AgentState] types
    Given the [Entity: AgentState] = <invalid_state>
    When the [Function: initialize_state] of [Component: WorkflowPlanner] is invoked
    Then a [Exception: ValueError] is thrown with message "Agent state must be a dictionary."

    Examples:
      | invalid_state         |
      | "not a dict"          |
      | 123                    |
      | [1,2,3]                |
      | null                   |

  @initialize_state @defaults
  Scenario: [Function: initialize_state] populates missing default keys
    Given the [Entity: AgentState] = {}
    When the [Function: initialize_state] of [Component: WorkflowPlanner] is invoked
    Then the returned [Entity: AgentState] contains keys:
      | allowed_nodes       |
      | available_nodes     |
      | subtasks            |
      | subtask_sequence    |
      | plan                |
      | current_step        |
      | workflow_valid      |
      | final_workflow      |
      | missing_nodes       |

  @decompose_task @error
  Scenario: [Function: decompose_task] raises error for missing or empty task
    Given the [Entity: AgentState] = {"allowed_nodes":[]}
    And no "task" key present
    When the [Function: decompose_task] of [Component: WorkflowPlanner] is invoked
    Then a [Exception: ValueError] is thrown with message "State must contain a non-empty 'task' string."

  @decompose_task @success
  Scenario: [Function: decompose_task] parses valid AI JSON into subtasks
    Given the [Entity: AgentState] = {"task": "A. B. C."}
    And the [Component: AIService] mock returns:
      """
      {"subtasks": ["A", "B", "C"], "sequence": ["A", "B", "C"]}
      """
    When the [Function: decompose_task] is invoked
    Then the [Entity: subtasks] equals ["A","B","C"]
    And the [Entity: subtask_sequence] equals ["A","B","C"]

  @create_initial_subtask_workflow @error
  Scenario: [Function: create_initial_subtask_workflow] raises error for missing task
    Given the [Entity: AgentState] without "task" key
    When the [Function: create_initial_subtask_workflow] of [Component: WorkflowPlanner] is invoked
    Then a [Exception: ValueError] is thrown with message "Agent state must include a non-empty 'task' string."

  Scenario: [Function: create_initial_subtask_workflow] handles missing subtasks key
    Given the [Entity: AgentState] = {"task": "Test task"}
    When the [Function: create_initial_subtask_workflow] is invoked
    Then the state should contain an empty "subtasks" list

  @create_initial_subtask_workflow @success
  Scenario: [Function: create_initial_subtask_workflow] builds plan from AI dict JSON
    Given the [Entity: AgentState] = {"task":"X","subtasks":["X"]}
    And the [Component: AIService] mock returns:
      """
      {"step":"X","input":["i"],"output":["o"],"tags":["t"],"description":"d","SPO":{"subject":"s","predicate":"p","object":"o"}}
      """
    When the [Function: create_initial_subtask_workflow] is invoked
    Then the [Entity: plan][0] contains:
      | step        | "X"       |
      | input       | ["i"]     |
      | output      | ["o"]     |
      | tags        | ["t"]     |
      | description | "d"       |
      | SPO         | ["s","p","o"] |

  @generate_plan_batch @failure
  Scenario: [Function: generate_plan_batch] handles node filtering error
    Given the [Entity: AgentState] = {"task":"T","subtasks":["T"],"plan":[{"step":"T"}],"available_nodes":[]}
    And the [Component: NodeService] mock returns string "error"
    When the [Function: generate_plan_batch] is invoked
    Then the [Entity: missing_node_error] is true
    And the [Entity: plan] remains unchanged

@generate_plan_batch @success
Scenario: [Function: generate_plan_batch] maps nodes into plan entries
  Given the [Entity: AgentState] with:
    | task                   | Content Creation Pipeline            |
    | subtasks              | ["Video Transcript Generation"]      |
    | subtask_sequence      | ["Video Transcript Generation"]      |
    | plan                  | [{"step":"Video Transcript Generation", "description":"Generate transcript from video", "input":["video_file"], "output":["transcript_text"]}] |
    | available_nodes       | ["Get_Youtube_Transcript"]           |
  And the [Component: NodeService] mock returns map:
    """
    {
      "Video Transcript Generation": [{
        "id": "Get_Youtube_Transcript",
        "input": ["youtube_url", "video_url"],
        "output": ["transcript"],
        "tags": ["YouTube", "Transcription"],
        "description": "Retrieves transcript from YouTube video"
      }]
    }
    """
  When the [Function: generate_plan_batch] is invoked
  Then the [Entity: plan][0] equals:
    | node_id               | Get_Youtube_Transcript    |
    | inputs               | ["youtube_url", "video_url"] |
    | output               | ["transcript"]              |
    | step                 | Video Transcript Generation |

  @generate_workflow_from_plan @error
  Scenario: [Function: generate_workflow_from_plan] raises error for non-list plan
    Given the [Entity: plan] = "not a list"
    When the [Function: generate_workflow_from_plan] is invoked
    Then a [Exception: ValueError] is thrown with message "Plan must be a list of steps."

  @generate_workflow_from_plan @structure
  Scenario: [Function: generate_workflow_from_plan] inserts start and end nodes
    Given the [Entity: plan] = [{"node_id":"A","inputs":[],"output":[]}]
    When the [Function: generate_workflow_from_plan] is invoked
    Then the [Entity: nodes] contains {"id":"__start__","type":"schema"}
    And the [Entity: nodes] contains {"id":"__end__","type":"schema"}
    And the [Entity: edges] includes {"source":"__start__","target":"A"} and {"source":"A","target":"__end__"}

  @execute_step @success
  Scenario: [Function: execute_step] increases step and validates workflow
    Given the [Entity: plan] with two steps
    And the [Entity: current_step] = 0
    When the [Function: execute_step] is invoked
    Then the [Entity: current_step] = 1
    And the [Entity: workflow_valid] = true
    And the [Entity: final_workflow] is generated

  @execute_step @no_plan
  Scenario: [Function: execute_step] handles empty plan gracefully
    Given the [Entity: plan] = []
    When the [Function: execute_step] is invoked
    Then the [Entity: workflow_valid] = false

  @map_workflow_edges @error
  Scenario: [Function: map_workflow_edges] raises error for missing final_workflow
    Given the [Entity: AgentState] without "final_workflow"
    When the [Function: map_workflow_edges] is invoked
    Then a [Exception: ValueError] is thrown with message "Final workflow is missing in state."

  @map_workflow_edges @success
  Scenario: [Function: map_workflow_edges] updates state on valid AI mapping
    Given the [Entity: AgentState] with "final_workflow":{"main":{}}, "initial_workflow":{}, "plan":[{}]
    And the [Component: AIService] mock returns valid JSON:
      """
      {"main":{"state":{"mainstate":"X"},"edges":[{"source":"A","target":"B"}]}}
      """
    When the [Function: map_workflow_edges] is invoked
    Then the [Entity: final_workflow]["main"]["state"]["mainstate"] = "GraphState"
    And the [Entity: final_workflow]["main"]["edges"] contains {"source":"A","target":"B"}