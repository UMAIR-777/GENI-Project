
Feature: [Component: EmbeddingService] Initialization and Model Loading  
  As a [User: Developer]  
  I want the [Class: EmbeddingService] to initialize cleanly  
  so that either a local [Component: SentenceTransformer] model is loaded or a provided [Component: InferenceClient] is used  
  and all initialization errors are surfaced and logged.

  Scenario: [UserAction: Valid local model exists]  
    Given the environment variable [EnvVar: EMBEDDING_MODEL] is set to "my-model"  
    And the environment variable [EnvVar: LOCAL_MODEL_PATH] is set to "/models"  
    And the directory [DirPath: /models/my-model] exists on the filesystem  
    When I create a new instance of [Class: EmbeddingService]  
    Then no exception of type [Exception: Exception] is thrown  
    And the [Component: SentenceTransformer] model is loaded from [DirPath: /models/my-model]  
    And an [Log: INFO] entry containing "Local model loaded from /models/my-model" is recorded  

  Scenario: [UserAction: Missing EMBEDDING_MODEL var]  
    Given the environment variable [EnvVar: EMBEDDING_MODEL] is not set  
    And the environment variable [EnvVar: LOCAL_MODEL_PATH] is set to "/models"  
    When I create a new instance of [Class: EmbeddingService]  
    Then an exception of type [Exception: ValueError] is thrown  
    And an [Log: ERROR] entry containing "EMBEDDING_MODEL must be set" is recorded  

  Scenario: [UserAction: Missing LOCAL_MODEL_PATH var]  
    Given the environment variable [EnvVar: EMBEDDING_MODEL] is set to "my-model"  
    And the environment variable [EnvVar: LOCAL_MODEL_PATH] is not set  
    When I create a new instance of [Class: EmbeddingService]  
    Then an exception of type [Exception: TypeError] is thrown  
    And an [Log: ERROR] entry containing "os.path.join" is recorded  

  Scenario: [UserAction: Provided InferenceClient skips local model]  
    Given a stubbed [Component: InferenceClient] is provided to [Class: EmbeddingService]  
    When I create a new instance of [Class: EmbeddingService]  
    Then no exception is thrown  
    And the [Component: SentenceTransformer] is not loaded  
    And an [Log: INFO] entry "InferenceClient is provided, skipping local model loading." is recorded  

  Scenario: [Chaos: Download success path]  
    Given the environment variable [EnvVar: EMBEDDING_MODEL] is set to "remote-model"  
    And the directory [DirPath: /models/remote-model] does not exist  
    And the environment variable [EnvVar: HF_API_TOKEN] is set to "valid-token"  
    When downloading the model via [API: SentenceTransformer(model_name)] succeeds  
    Then the directory [DirPath: /models/remote-model] is created  
    And the [Component: SentenceTransformer] model is saved to [DirPath: /models/remote-model]  
    And an [Log: INFO] entry containing "Model downloaded and saved to /models/remote-model" is recorded  

  Scenario: [Chaos: Download failure due to invalid token]  
    Given the environment variable [EnvVar: EMBEDDING_MODEL] is set to "private-model"  
    And the directory [DirPath: /models/private-model] does not exist  
    And the environment variable [EnvVar: HF_API_TOKEN] is not set  
    When downloading the model via [API: SentenceTransformer(model_name)] is attempted  
    Then an exception of type [Exception: ValueError] is thrown  
    And an [Log: ERROR] entry containing "HF_API_TOKEN must be set" is recorded  

# ----------- Failed ------------
  Scenario: [Chaos: Runtime error during download]  
    Given the environment variable [EnvVar: EMBEDDING_MODEL] is set to "private-model"  
    And the directory [DirPath: /models/private-model] does not exist  
    And the environment variable [EnvVar: HF_API_TOKEN] is set to "valid-token"  
    When the call to [API: SentenceTransformer(model_name)] raises [Exception: RuntimeError]  
    Then an exception of type [Exception: RuntimeError] is thrown  
    And an [Log: ERROR] entry containing "Error downloading or saving local model" is recorded  

  Scenario Outline: [PropertyBased: Parameterized missing env vars]  
    Given the environment variable [EnvVar: <var>] is <state>  
    When I create a new instance of [Class: EmbeddingService]  
    Then an exception of type [Exception: ValueError] is thrown  
    And an [Log: ERROR] entry with "<message>" is recorded  

    Examples:  
      | var             | state    | message                                   |
      | EMBEDDING_MODEL | not set  | "EMBEDDING_MODEL must be set"             |
      | HF_API_TOKEN    | not set  | "HF_API_TOKEN must be set"                |

Feature: [Function: get_embeddings] Text Embedding Generation  
  As a [User: Developer]  
  I want the [Function: get_embeddings] to validate input and return non-empty embeddings  
  so that invalid inputs are rejected and valid text yields a list of floats.

  Scenario: [HappyPath: Valid short text]  
    Given the string [Type: str] "Hello world"  
    When I call [Function: get_embeddings] with this input  
    Then it returns a [Type: list] of floats  
    And the returned list length is greater than 0  

  Scenario: [InputValidation: Non-string input]  
    Given the input [Type: int] 12345  
    When I call [Function: get_embeddings]  
    Then an exception of type [Exception: ValueError] is thrown  
    And the message contains "must be a string"  

  Scenario: [InputValidation: Empty string]  
    Given the string [Type: str] ""  
    When I call [Function: get_embeddings]  
    Then an exception of type [Exception: ValueError] is thrown  
    And the message contains "must not be empty or whitespace"  

  Scenario: [InputValidation: Whitespace string]  
    Given the string [Type: str] "   "  
    When I call [Function: get_embeddings]  
    Then an exception of type [Exception: ValueError] is thrown  
    And the message contains "must not be empty or whitespace"  

  Scenario: [Chaos: Model.encode returns empty numpy array]  
    Given a stubbed [API: model.encode] returns [Type: numpy.ndarray] []  
    When I call [Function: get_embeddings] with "test"  
    Then an exception of type [Exception: RuntimeError] is thrown  
    And the message contains "Embedding generation returned an empty result"  

  Scenario: [Chaos: Model.encode returns list]  
    Given a stubbed [API: model.encode] returns [Type: list] [0.1, 0.2, 0.3]  
    When I call [Function: get_embeddings] with "test"  
    Then it returns the same [Type: list] [0.1, 0.2, 0.3]  

  Scenario: [Chaos: Unexpected return type]  
    Given a stubbed [API: model.encode] returns [Type: dict] {"a":1}  
    When I call [Function: get_embeddings] with "test"  
    Then an exception of type [Exception: RuntimeError] is thrown  
    And the message contains "Unexpected type returned"  

  Scenario Outline: [PropertyBased: Parameterized text inputs]  
    Given the string [Type: str] "<text>"  
    When I call [Function: get_embeddings]  
    Then it returns a [Type: list]  
    And no exception is thrown  

    Examples:  
      | text          |
      | "a"           |
      | "long text..."|
      | "特殊字符"     |

Feature: [Function: normalize_embedding] Vector Normalization  
  As a [User: Developer]  
  I want the [Function: normalize_embedding] to normalize non-zero vectors and reject invalid ones  
  so that downstream cosine computations remain valid.

  Scenario: [HappyPath: Valid numeric vector]  
    Given the numpy array [Type: numpy.ndarray] [3.0, 4.0]  
    When I call [Function: normalize_embedding]  
    Then it returns the list [0.6, 0.8]  

  Scenario: [InputValidation: Empty list input]  
    Given the list [Type: list] []  
    When I call [Function: normalize_embedding]  
    Then an exception of type [Exception: ValueError] is thrown  
    And the message contains "Embedding is empty"  

  Scenario: [InputValidation: Zero vector]  
    Given the list [Type: list] [0.0, 0.0]  
    When I call [Function: normalize_embedding]  
    Then an exception of type [Exception: ValueError] is thrown  
    And the message contains "norm is zero"  

  Scenario: [InputValidation: Invalid type]  
    Given the input [Type: str] "not-array"  
    When I call [Function: normalize_embedding]  
    Then an exception of type [Exception: ValueError] is thrown  
    And the message contains "must be provided as a list or numpy array"  

  Scenario: [HappyPath: List input normalization]  
    Given the list [Type: list] [1.0, 2.0, 2.0]  
    When I call [Function: normalize_embedding]  
    Then it returns a list whose Euclidean norm is 1.0  

  Scenario Outline: [PropertyBased: Various vector lengths]  
    Given the list [Type: list] <vector>  
    When I call [Function: normalize_embedding]  
    Then the returned list has Euclidean norm 1.0  

    Examples:  
      | vector            |
      | [5.0, 0.0, 0.0]   |
      | [0.0, 3.0, 4.0]   |
      | [1.0, 1.0, 1.0]   |

Feature: [Function: generate_and_store_node_embeddings] Batch Node Processing & DB Storage  
  As a [User: Developer]  
  I want [Function: generate_and_store_node_embeddings] to process node lists and upsert embeddings into the [Database: PostgreSQL]  
  so that valid nodes are stored, invalid nodes are skipped, and database errors are handled gracefully.

  Scenario: [HappyPath: Single well-formed node]  
    Given the list [Type: list] contains one dictionary with keys [Key: id, input, output, tags, description, SPO]  
    And a stubbed [Function: get_embeddings] returns [Type: list] [0.1,0.2]  
    And a stubbed [Function: normalize_embedding] returns [Type: list] [0.447,0.894]  
    And the [Database: PostgreSQL] connection is available  
    And the [Table: node_embeddings] exists  
    When I call [Function: generate_and_store_node_embeddings]  
    Then no exception is thrown  
    And one INSERT INTO [Table: node_embeddings] is executed  
    And an [Log: INFO] entry containing "Successfully stored node embeddings in the database." is recorded  

  Scenario: [EdgeCase: Empty node list]  
    Given the list [Type: list] is empty  
    When I call [Function: generate_and_store_node_embeddings]  
    Then an exception of type [Exception: ValueError] is thrown  
    And the message contains "must be a non-empty list"  

  Scenario: [ErrorHandling: Node missing required keys]  
    Given the list [Type: list] contains one dictionary missing the key [Key: id]  
    When I call [Function: generate_and_store_node_embeddings]  
    Then no exception propagates  
    And an [Log: ERROR] entry containing "Node is missing the required 'id' key" is recorded  

  Scenario: [ErrorHandling: Node with empty descriptions]  
    Given the list [Type: list] contains one dictionary where [Key: description] is an empty list  
    When I call [Function: generate_and_store_node_embeddings]  
    Then no exception propagates  
    And an [Log: ERROR] entry containing "must have a non-empty 'description' list" is recorded  

  Scenario: [ErrorHandling: Node with incomplete SPO]  
    Given the list [Type: list] contains one dictionary where [Key: SPO] is missing "object"  
    When I call [Function: generate_and_store_node_embeddings]  
    Then no exception propagates  
    And an [Log: ERROR] entry containing "must have complete 'SPO' information" is recorded  

  Scenario: [Chaos: DB table missing triggers skip]  
    Given the [Database: PostgreSQL] returns pgcode '42P01' for table [Table: node_embeddings]  
    When I call [Function: generate_and_store_node_embeddings]  
    Then no exception propagates  
    And an [Log: INFO] entry containing "Table 'node_embeddings' does not exist; skipping node embedding storage." is recorded  

  Scenario: [Chaos: DB connection failure]  
    Given the environment variables for [EnvVar: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT] are set  
    And the [Database: PostgreSQL] connection attempt raises [Exception: OperationalError]  
    When I call [Function: generate_and_store_node_embeddings]  
    Then an exception of type [Exception: RuntimeError] is thrown  
    And an [Log: ERROR] entry containing "Failed to establish a database connection" is recorded  

  Scenario: [BulkInsert: Multiple valid nodes upsert]  
    Given the list [Type: list] contains two well-formed node dictionaries  
    And both [Key: node_id] values already exist in [Table: node_embeddings]  
    When I call [Function: generate_and_store_node_embeddings]  
    Then a single UPSERT using INSERT ... ON CONFLICT is executed for both rows  
    And no exception is thrown  
    And an [Log: INFO] entry containing "Successfully stored node embeddings in the database." is recorded  

  Scenario: [Mixed: Valid and invalid nodes in batch]  
    Given the list [Type: list] contains one valid node dictionary and one dictionary missing [Key: input]  
    When I call [Function: generate_and_store_node_embeddings]  
    Then only the valid node is upserted  
    And an [Log: ERROR] entry for the invalid node is recorded  
    And an [Log: INFO] entry "Successfully stored node embeddings in the database." is recorded  

  Scenario: [Performance: Large batch processing]  
    Given the list [Type: list] contains 1000 well-formed node dictionaries  
    When I call [Function: generate_and_store_node_embeddings]  
    Then execution completes within [Threshold: 2000ms]  
    And no exceptions are thrown  

  Scenario Outline: [PropertyBased: Parameterized node batches]  
    Given the list [Type: list] contains <count> well-formed node dictionaries  
    When I call [Function: generate_and_store_node_embeddings]  
    Then no exception is thrown  
    And exactly <count> rows are upserted  

    Examples:  
      | count |
      | 0     |
      | 1     |
      | 10    |
      | 100   |

  Scenario: [ModelBased: Simulate external API failures and retries]  
    Given a stubbed [Component: InferenceClient] that fails twice then succeeds  
    And the [Table: node_embeddings] exists  
    When I call [Function: generate_and_store_node_embeddings] with one node  
    Then the get_embeddings call is retried up to 3 times  
    And the embedding is eventually upserted  
    And an [Log: INFO] entry "Generated embeddings for node" is recorded  

  Scenario: [Solver: Validate embedding vector constraints]  
    Given the constraint that embedding length must be between 1 and 1024  
    And a proposed embedding of length 0  
    When I run the Z3 [Solver: constraint checker]  
    Then the solver reports unsatisfiable  
    And a [Log: ERROR] entry "Embedding size out of allowed range" is recorded  

# Download Model Not Important

  # Scenario: [Chaos: Successful model download]
  #   Given the environment variable EMBEDDING_MODEL is set to "model"
  #   And the directory /models/model does not exist
  #   And the environment variable HF_API_TOKEN is set to "valid-token"
  #   When downloading the model via SentenceTransformer("model") succeeds
  #   Then the directory /models/model is created
  #   And the model is saved successfully
  #   And an [Log: INFO] entry containing "Model downloaded and saved to /models/model" is recorded

  # Scenario: [Chaos: Download failure due to invalid model name]
  #   Given the environment variable EMBEDDING_MODEL is set to "invalid-model"
  #   And the directory /models/invalid-model does not exist
  #   And the environment variable HF_API_TOKEN is set to "valid-token"
  #   When the call to SentenceTransformer("invalid-model") raises ValueError
  #   Then an exception of type RuntimeError is thrown
  #   And an [Log: ERROR] entry containing "Load error" is recorded
    
  # Scenario: [Chaos: Permission denied during model download]
  #   Given the environment variable EMBEDDING_MODEL is set to "model"
  #   And the directory /models/model does not exist
  #   And the environment variable HF_API_TOKEN is set to "valid-token"
  #   When os.makedirs raises PermissionError
  #   Then an exception of type RuntimeError is thrown
  #   And an [Log: ERROR] entry containing "Error downloading or saving local model" is recorded

  # Scenario: [Chaos: Runtime error during download]
  #   Given the environment variable EMBEDDING_MODEL is set to "private-model"
  #   And the directory /models/private-model does not exist
  #   And the environment variable HF_API_TOKEN is set to "valid-token"
  #   When the call to SentenceTransformer("private-model") raises RuntimeError
  #   Then an exception of type RuntimeError is thrown
  #   And an [Log: ERROR] entry containing "Error downloading or saving local model" is recorded
