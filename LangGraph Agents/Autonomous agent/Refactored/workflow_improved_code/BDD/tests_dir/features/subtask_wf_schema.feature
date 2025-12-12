Feature: [File: subtask_workflow.py] Create Initial Subtask Workflow Blueprint
  As a [User: Developer] I want to execute [Function: create_initial_subtask_workflow] in [File: subtask_workflow.py] so that a complex task is decomposed into a detailed blueprint of subtasks and an actionable plan, ensuring 100% blueprint accuracy and full fallback activation under error conditions (KPI: 100% Accurate Blueprint).
  
  Scenarios:
    - Scenario: [UserAction: Successful Blueprint Generation]
        Given:
          - step: "Given the [File: subtask_workflow.py] contains [Function: create_initial_subtask_workflow] (S: File: subtask_workflow.py; P: defines; O: Function create_initial_subtask_workflow; Attributes: {Role: 'Workflow Blueprint Generator', State: 'Active', KPI: 'Defined 100%'})"
          - step: "And the [State: AgentState] provided contains a non-empty 'task' string (S: State: AgentState; P: contains; O: Key 'task' with value 'Complex business task description'; Attributes: {EntityType: 'State', Role: 'Task Descriptor', KPI: 'Input Validity 100%'})"
          - step: "And the [Component: PromptManager] (S: Class: PromptManager; P: initialized in; O: File: prompt_manager.py; Attributes: {EntityType: 'Class', Role: 'Template Renderer', State: 'Initialized', KPI: 'Template Availability 100%'}) is ready to render the 'subtask/create_blueprint.jinja2' template (S: Template: subtask/create_blueprint.jinja2; P: is used by; O: Function create_initial_subtask_workflow; Attributes: {EntityType: 'Template', Role: 'Blueprint Provider', KPI: '100% Template Readiness'})"
        When:
          - step: "When the [TestFramework: Pytest] invokes [Function: create_initial_subtask_workflow] with the current AgentState (S: TestFramework: Pytest; P: invokes; O: Function create_initial_subtask_workflow; Attributes: {EntityType: 'Function', TestType: 'Integration Test', Input: 'Valid AgentState', KPI: 'Execution 100%'})"
          - step: "And the [Function: Ask_AI] is called internally to return a JSON response containing a valid blueprint (S: Function: Ask_AI; P: is invoked by; O: Function create_initial_subtask_workflow; Attributes: {EntityType: 'Function', Role: 'LLM Query', KPI: 'LLM Response Validity 100%'})"
        Then:
          - step: "Then the [Output: AgentState] must be updated with a non-empty 'plan' key containing a blueprint that follows the node embedding format (S: Output: AgentState; P: is updated with; O: Key 'plan' with valid JSON blueprint; Attributes: {EntityType: 'State', Validation: 'Blueprint Integrity', KPI: '100% Blueprint Accuracy'})"
          - step: "And each step in the 'plan' must have an added 'description_embed' field concatenating step details (S: Output: AgentState; P: has added; O: Field 'description_embed' in each plan step; Attributes: {EntityType: 'Data', Role: 'Enrichment', KPI: '100% Field Enrichment'})"
          
    - Scenario: [UserAction: Fallback Decomposition on Malformed AI Response]
        Given:
          - step: "Given the [File: subtask_workflow.py] contains [Function: create_initial_subtask_workflow] that attempts to parse AI output for blueprint creation (S: File: subtask_workflow.py; P: contains; O: Function create_initial_subtask_workflow; Attributes: {EntityType: 'Function', Role: 'Workflow Blueprint Generator', KPI: 'Parsing Expected'})"
          - step: "And the [State: AgentState] provided contains a valid non-empty 'task' string (S: State: AgentState; P: contains; O: Key 'task' with value 'Complex business task description'; Attributes: {EntityType: 'State', Role: 'Task Descriptor', KPI: 'Input Validity 100%'})"
        When:
          - step: "When the [TestFramework: Pytest] invokes [Function: create_initial_subtask_workflow] and [Function: Ask_AI] returns a malformed JSON string (S: TestFramework: Pytest; P: invokes; O: Function create_initial_subtask_workflow with malformed AI output; Attributes: {EntityType: 'Function', TestType: 'Negative Test', KPI: 'Fallback Activation 100%'})"
        Then:
          - step: "Then the [Output: AgentState] must be updated using a fallback strategy that splits the 'task' string on period delimiters to populate 'subtasks' and 'subtask_sequence' (S: Output: AgentState; P: is updated using; O: Fallback decomposition strategy 'split on period'; Attributes: {EntityType: 'State', Validation: 'Fallback Mechanism', KPI: '100% Fallback Accuracy'})"
          - step: "And a warning must be logged via [Component: Logger] indicating fallback activation (S: Component: Logger; P: logs; O: Warning 'Fallback decomposition applied'; Attributes: {EntityType: 'Logger', Role: 'Error Notification', KPI: '100% Error Capture'})"
