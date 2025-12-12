Feature: [Component:AIService.ask_ai] JSON Extraction and Error Handling
  As a [User:Developer]
  I want the [Component:AIService.ask_ai] to reliably return valid JSON strings or fail with clear errors
  so that downstream [Component:JSONParser] can process responses safely.

  Scenario: [Construct:AIService] with explicit model
    Given the [Class:AIService] is instantiated with [FunctionParameter:model] set to "gpt-test"
    Then a new [Instance:AIService] is created without error

  Scenario: [Construct:AIService] using environment variable
    Given the [EnvironmentVariable:MODEL_USED] is set to "gpt-env"
    When the [Class:AIService] is instantiated with no [FunctionParameter:model]
    Then a new [Instance:AIService] is created using model "gpt-env"

  Scenario: [Fail:MissingConfiguration] when no model is provided
    Given no [FunctionParameter:model] and no [EnvironmentVariable:MODEL_USED]
    When the [Class:AIService] is instantiated
    Then an [Exception:EnvironmentError] is raised

  Scenario Outline: [InputValidation] empty or whitespace prompts
    Given an [Instance:AIService] exists
    When the [Function:ask_ai] is called with prompt "<prompt>" and context "valid context"
    Then an [Exception:ValueError] is raised
  Examples:
    | prompt  |
    | ""      |
    | "   "   |

  Scenario Outline: [InputValidation] empty or whitespace contexts
    Given an [Instance:AIService] exists
    When the [Function:ask_ai] is called with prompt "valid prompt" and context "<context>"
    Then an [Exception:ValueError] is raised
  Examples:
    | context |
    | ""      |
    | "   "   |

  Scenario: [ErrorHandling] LLM invocation failure
    Given the [Instance:AIService] is configured
    And the [Library:ChatGroq] returns an error on invoke
    When the [Function:ask_ai] is called with valid inputs
    Then an [Exception:RuntimeError] is raised

  Scenario: [Failure:MissingContent] response missing content attribute
    Given the [Library:ChatGroq] returns an object without [Attribute:content]
    When the [Function:ask_ai] is called
    Then an [Exception:RuntimeError] is raised

  Scenario: [Parsing] no JSON in LLM response
    Given the [Library:ChatGroq] returns content "no json here"
    When the [Function:ask_ai] is called
    Then an [Exception:RuntimeError] is raised

  Scenario: [Parsing] invalid JSON structure
    Given the [Library:ChatGroq] returns content "{invalid: json}"
    When the [Function:ask_ai] is called
    Then an [Exception:RuntimeError] is raised

  Scenario: [HappyPath] valid JSON response
    Given the [Library:ChatGroq] returns content "{ \"key\": \"value\" }"
    When the [Function:ask_ai] is called with valid inputs
    Then the returned string matches JSON schema