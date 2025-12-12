Feature: [Function: Ask_AI]
  As a [Developer: PromptEngineer] I want to robustly extract valid JSON from [LLM_Response: ChatGroq] using the [Function: Ask_AI] function so that I can rely on consistent structure for downstream processing, with safe error handling and measurable performance.

  # --- Core Flow Scenarios ---
  Scenario: [CUJ: HappyPath] Valid prompt and valid JSON returned
    Given a [String:prompt] with meaningful content
    And a [String:context] requesting JSON structure
    When the [Function: Ask_AI] is called with valid [Input: prompt] and [Input: context]
    Then it should call [API: ChatGroq.invoke()] and return a valid [String:JSON]
    And the [Regex: JSON extractor] should match one valid JSON object or array

  # --- Input Validation Edge Cases ---
  Scenario: [CUJ: InvalidPrompt] Prompt is empty or non-string
    Given an [Input: prompt] that is empty or non-string
    And a valid [Input: context] string
    When [Function: Ask_AI] is called
    Then a [Exception: ValueError] should be raised indicating invalid prompt

  Scenario: [CUJ: InvalidContext] Context is empty or non-string
    Given a valid [Input: prompt] string
    And an [Input: context] that is empty or non-string
    When [Function: Ask_AI] is called
    Then a [Exception: ValueError] should be raised indicating invalid context

  Scenario: [CUJ: MaxLengthPrompt] Prompt exceeds maximum safe token size
    Given a [String:prompt] exceeding [Config: token_limit]
    And a valid [String:context]
    When [Function: Ask_AI] is called
    Then it should raise a [Exception: ValueError] for length overflow

  Scenario: [CUJ: UnicodePrompt] Prompt contains unicode characters or emojis
    Given a [String:prompt] with unicode or emoji characters
    When [Function: Ask_AI] is called
    Then the output JSON should still be correctly parsed

  # --- LLM Response Failures ---
  Scenario: [CUJ: RegexMismatch] No valid JSON structure in LLM response
    Given a valid [Input: prompt] and [Input: context]
    And the [LLM_Response: response.content] does not contain any JSON
    When [Function: Ask_AI] is called
    Then a [Exception: RuntimeError] should be raised due to JSON extraction failure
    And a log message should be recorded in the [Logger: module logger]

  Scenario: [CUJ: MalformedJSON] Regex finds a match but JSON is invalid
    Given a valid [Input: prompt] and [Input: context]
    And the [LLM_Response: response.content] contains malformed JSON
    When [Function: Ask_AI] attempts to parse it
    Then a [Exception: RuntimeError] should be raised with appropriate logs

  Scenario: [CUJ: TimeoutFromLLM] LLM client throws a timeout or network error
    Given valid [Input: prompt] and [Input: context]
    And the [Function: ChatGroq.invoke()] raises a [Exception: TimeoutError]
    When [Function: Ask_AI] is called
    Then a [Exception: RuntimeError] should be raised with error details logged

  Scenario: [CUJ: RetryLogic] Temporary failure from LLM client is recoverable
    Given the first call to [Function: ChatGroq.invoke()] fails
    And the second retry succeeds with a valid response
    When [Function: Ask_AI] is invoked with retry logic
    Then the final returned output should be valid JSON

  Scenario: [CUJ: MaxRetriesExceeded] All retries to LLM fail
    Given 3 attempts to [API: ChatGroq.invoke()] fail
    When [Function: Ask_AI] is invoked
    Then a [Exception: RuntimeError] should be raised with retry summary

  Scenario: [CUJ: UnexpectedErrorFromLLM] ChatGroq raises unexpected internal exception
    Given [Function: ChatGroq.invoke()] raises an unknown error
    When [Function: Ask_AI] is called
    Then a [Exception: RuntimeError] should be raised with traceback captured in logs

  # --- Environment Configuration ---
  Scenario: [CUJ: MissingEnvVar] Environment variable MODEL_USED not set
    Given the [EnvironmentVariable: MODEL_USED] is missing
    When the [Module: llm_ai.py] is loaded
    Then an [Exception: EnvironmentError] should be raised with a clear message

  Scenario: [CUJ: InvalidEnvValue] MODEL_USED is set but not supported
    Given the [EnvironmentVariable: MODEL_USED] has invalid model name
    When the [Module: llm_ai.py] is initialized
    Then a [Exception: RuntimeError] should be raised indicating configuration failure

  # --- Performance and Edge Boundaries ---
  Scenario: [CUJ: SlowRegex] Extremely large response triggers performance warning
    Given a large [LLM_Response: response.content] string
    When [Regex: JSON extractor] is applied
    Then the operation should complete within performance SLA (e.g., < 100ms)
    And benchmark logs should be generated

  Scenario: [CUJ: EdgeCaseBrackets] Nested or misleading brackets confuse regex
    Given a [LLM_Response: response.content] with tricky nested structures
    When [Regex: JSON extractor] runs
    Then the correct JSON block should still be extracted

  Scenario: [CUJ: JSONArraySupport] LLM returns an array instead of object
    Given the [LLM_Response: response.content] contains a JSON array
    When [Regex: JSON extractor] runs
    Then the output should still validate as proper JSON

  Scenario: [CUJ: JSONDeepNesting] Deeply nested JSON object
    Given the [LLM_Response: response.content] contains nested fields
    When [Function: Ask_AI] parses it
    Then the full nested structure should be returned without truncation

  # --- System Configuration Validation ---
  Scenario: [CUJ: ConfigValidation] Robust .env loading and MODEL_USED verification
    Given the [File: .env] contains a valid [Key: MODEL_USED]
    When the module loads
    Then the [Variable: model_used] should be initialized correctly

  Scenario: [CUJ: LoggingCoverage] All errors and decisions are logged
    Given a runtime error occurs
    When [Function: Ask_AI] handles it
    Then an error log should exist in [Logger: module logger] with context

  Scenario: [CUJ: UnicodeResponse] LLM returns non-ASCII or encoded JSON
    Given the [LLM_Response: response.content] includes escaped unicode
    When parsed by [Function: Ask_AI]
    Then a valid [String:JSON] should still be returned

  Scenario: [CUJ: RegexTimeoutSimulation] Simulate regex engine hang
    Given a crafted [LLM_Response: response.content] that triggers catastrophic backtracking
    When [Regex: JSON extractor] runs
    Then the system should abort or timeout within a safe bound

  Scenario: [CUJ: ExternalDependencyMocking] LLM client is mocked during test
    Given a [Mock: ChatGroq] is injected
    When [Function: Ask_AI] is called
    Then the [Mock: ChatGroq.invoke()] should simulate responses for isolated testing

