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