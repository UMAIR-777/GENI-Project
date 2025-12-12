Feature: [Story: EvalMetricsGeneration] As a [User: Developer] I want to generate evaluation metrics for AI prompts so that I can ensure robust, high-quality output.
  Background:
    Given the [Component: EnvLoader] has loaded [.env] variables
    And the [Component: TemplateLoader] has loaded [Directory: templates]

  @happy_path
  Scenario: [FunctionCall: generate_eval_metrics()] Happy Path Metric Generation
    Given a valid [Function: generate_eval_metrics] request with [Parameter: role="Tester"] and [Parameter: task="SampleTask"]
    When the [Component: JinjaEngine] renders the [Template: eval_template.jinja2]
    And the [API: ChatGroq.invoke] is called with the rendered prompt
    Then the [FunctionComponent: _clean_markdown_json] returns a clean JSON string
    And the [Function: json.loads] parses the metrics
    And the [Condition: metrics list length] is greater than or equal to [KPI: top_n=7]
    And the [Function: sorted] selects the top 7 metrics by [Attribute: insight_score]
    And the [Component: Logger] logs "Top 7 metrics generated"

  @edge_case @boundary
  Scenario Outline: [ErrorHandling: Malformed JSON Output] Handles Invalid LLM Response
    Given the LLM returns a response with <malformed>
    When the [FunctionComponent: _clean_markdown_json] is applied to the response
    Then the [Condition: cleaned string] should not include markdown fences
    And calling [Function: json.loads] raises <exception>
    And the [Component: ExceptionHandler] catches <exception>
    Examples:
      | malformed                   | exception               |
      | "```json {invalid} ```"      | JSONDecodeError         |
      | "random text not JSON"      | ValueError              |

  @performance @scalability
  Scenario: [Performance: Partial Sort] Optimize Sorting for Large Metric Lists
    Given a metrics list of size [State: 10000]
    When the [Component: PartialSorter] uses [Function: heapq.nlargest] to select [KPI: top_n=7]
    Then the [Condition: time complexity] should be O(n log k)
    And the [Condition: memory overhead] remains minimal

  @dependency @failover
  Scenario: [DependencyValidation: Config Check] Fail-Fast on Missing Environment
    Given the [.env] file is missing [Key: MODEL_USED]
    When the [Component: EnvLoader] loads variables
    Then the [Component: ConfigValidator] raises [Error: MissingConfigError]
    And the [Function: sys.exit] is called with code [Value:1]

  @model_based
  Scenario: [SystemModel: LLM Invocation Flow] Model-Based State Transitions
    Given the system is in [State: ReadyForLLM]
    When the action [Action: invoke_llm] is executed
    Then the system transitions to [State: ParsingResponse]
    And on [Event: success] transitions to [State: MetricsReady]
    And on [Event: timeout] transitions to [State: RetryPending]
    And on [Event: invalid_json] transitions to [State: ErrorState]

  @chaos @unexpected
  Scenario: [Chaos: Network Failure Recovery] Chaos Engineering
    Given the network call to ChatGroq API is delayed or fails intermittently
    When the [Component: LLMInvoker] experiences <network_failure>
    Then the [Strategy: exponential backoff] should retry up to [KPI:3] times
    And on persistent failure the [Component: CircuitBreaker] opens
    And the [Function: notify_admin] is invoked
    
Feature: [Component:ToolIntegration] As a [User:Developer] I want to insert [Concept:ToolCallStubs] into [File:class_functions.py] so that [KPI:FutureActionability] and [KPI:Maintainability] are maximized.

  @happy_path @property_based
  Scenario Outline: [FunctionComponent:insert_tool_calls] produces correct stubs for various tool list sizes
    Given a [FunctionComponent:generate_eval_metrics] with a [Concept:ToolCallList] of <count> tool(s) named <tools>
    When the [FunctionComponent:insert_tool_calls] is executed
    Then the [File:class_functions.py] contains <count> occurrences of [FunctionCall:call_tool('<tool>')]

    Examples:
      | count | tools                                                    | tool         |
      | 1     | ["ToolA"]                                                | ToolA        |
      | 2     | ["ToolA","ToolB"]                                        | ToolA,ToolB  |
      | 5     | ["T1","T2","T3","T4","T5"]                               | T1,T2,T3,T4,T5 |

  @edge_case @boundary
  Scenario: Empty [Concept:ToolCallList] results in no stubs
    Given a [FunctionComponent:generate_eval_metrics] with an empty [Concept:ToolCallList]
    When the [FunctionComponent:insert_tool_calls] is executed
    Then the [File:class_functions.py] contains no occurrences of [FunctionCall:call_tool]

  @input_validation @failure_mode
  Scenario: Non-string tool name triggers validation error
    Given a [FunctionComponent:generate_eval_metrics] with a [Concept:ToolCallList] containing [Integer:123]
    When the [FunctionComponent:insert_tool_calls] is executed
    Then a [Concept:ValidationError] is thrown with message matching /tool names must be strings/

  @boundary @performance
  Scenario: Tool list size exceeds maximum limit causes error
    Given a [FunctionComponent:generate_eval_metrics] with a [Concept:ToolCallList] of 101 tool names
    When the [FunctionComponent:insert_tool_calls] is executed
    Then a [Concept:ValueError] is thrown with message matching /too many tool calls/

  @chaos_engineering @robust_error_handling
  Scenario: File system error during stub insertion triggers retry logic
    Given the [Component:FileSystem] is mocked to raise [Exception:IOError] on write
    And a [FunctionComponent:generate_eval_metrics] with a [Concept:ToolCallList] of ["ToolX"]
    When the [FunctionComponent:insert_tool_calls] is executed
    Then the [Function:retry_logic] is invoked up to [Integer:3] times with exponential backoff
    And a [Log:warning] is recorded for each retry attempt
    And the final outcome is a [Concept:LLMInvocationError] after retries exhausted

  @model_based @state_transition
  Scenario: State transition from no stubs to stubs injected
    Given the system is in [State:NoStubs]
    When the [Action:InjectToolStubs] occurs with a [Concept:ToolCallList] of ["ToolY","ToolZ"]
    Then the system transitions to [State:StubsInjected]
    And the [State:StubsInjected] includes [FunctionCall:call_tool("ToolY")] and [FunctionCall:call_tool("ToolZ")]

  @integration @model_based
  Scenario: Mock external API calls during tool stub generation
    Given the [API:ChatGroq.invoke] is mocked to return a JSON with "tools":["ToolA","ToolB"]
    When the [FunctionComponent:run_ai_step_node] is executed
    Then the [FunctionComponent:insert_tool_calls] in [File:class_functions.py] is called with ["ToolA","ToolB"]
