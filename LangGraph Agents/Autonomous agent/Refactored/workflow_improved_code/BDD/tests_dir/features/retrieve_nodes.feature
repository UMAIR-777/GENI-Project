BDD_FEATURES: |
  Feature: [Module: BatchNodeRetrieval] - As a [Role: DataEngineer] I want to perform batch retrieval of similar nodes using two-stage filtering [KPI: SQL Query Latency < 200ms, Node Matching Accuracy ≥ 99%] so that the system reliably returns accurate candidate nodes for each blueprint step even under critical conditions.

  Scenario: [UserAction: Valid Batch Retrieval]
    Given [S:File: blueprint_steps.json] [P:provides] [O:valid blueprint step data {input, output, tags, description, SPO}] 
    And [S:Class: BlueprintStep] [P:is instantiated with] [O:valid attributes {input, output, tags, description, SPO}] from [File: blueprint_steps.json]
    When [S:Function: get_embeddings] [P:is invoked with] [O:concatenated text from {input}] extracted from [Class: BlueprintStep]
    And [S:Function: normalize_embedding] [P:processes] [O:raw embeddings computed by get_embeddings]
    And [S:Function: format_embeddings_for_sql] [P:formats] [O:embedding lists into SQL-ready strings] for each attribute {input, output, tags, description, SPO}
    And [S:Database: pool] [P:establishes] [O:a connection to PostgreSQL as configured in {db_connection.cfg}]
    And [S:StoredProcedure: retrieve_similar_nodes_twostep_batch] [P:is executed via] [O:SQL SELECT statement with formatted embeddings]
    Then [S:Function: retrieve_similar_nodes_batch] [P:maps] [O:SQL result rows (8 columns) to corresponding BlueprintStep using attribute {step}]
    And [S:Variable: similar_nodes_by_query] [P:is populated with] [O:candidate node tuples ensuring Node Matching Accuracy ≥ 99%]
    And [S:Logging: logger] [P:logs] [O:an INFO event with the number of retrieved candidate nodes]

  Scenario: [UserAction: Handling Empty Blueprint Steps]
    Given [S:Input: Empty List] [P:is provided to] [O:Function retrieve_similar_nodes_batch] from [Module: DataPreprocessing]
    When [S:Function: retrieve_similar_nodes_batch] [P:verifies] [O:blueprint_steps list length equals 0]
    Then [S:Library: logging] [P:logs] [O:an ERROR event "Blueprint steps list is empty" at Level: error]
    And [S:Function: retrieve_similar_nodes_batch] [P:raises] [O:ValueError with message "Blueprint steps list is empty"]

  Scenario: [UserAction: Handling Malformed Embedding Data]
    Given [S:Function: get_embeddings] [P:returns] [O:malformed or unexpected embedding data] for a [Class: BlueprintStep] instance from [Module: EmbeddingUtil]
    When [S:Function: normalize_embedding] [P:processes] [O:the malformed embedding data and encounters an unexpected format]
    Then [S:Library: logging] [P:logs] [O:a WARNING event with details of the Embedding Normalization Error using [Tool: Sentry] integration]
    And [S:Function: retrieve_similar_nodes_batch] [P:skips] [O:the faulty embedding ensuring processing continues for valid blueprint steps with Error Rate ≤ 0.1%]

  Scenario: [UserAction: Handling SQL Execution Failure]
    Given [S:Database: pool] [P:establishes] [O:a connection using configuration from {db_connection.cfg}]
    And [S:StoredProcedure: retrieve_similar_nodes_twostep_batch] [P:is invoked via] [O:SQL SELECT statement with formatted embeddings]
    When [S:SQL Engine] [P:encounters] [O:a SQL Execution Error (e.g., Network Timeout or Query Error)]
    Then [S:Library: logging] [P:logs] [O:an ERROR event with a detailed Exception Stack Trace at Level: error]
    And [S:Function: conn.rollback] [P:is executed to] [O:revert any partial changes]
    And [S:Function: retrieve_similar_nodes_batch] [P:raises] [O:a DatabaseError to the caller ensuring Critical Failure Recovery]

  Scenario: [UserAction: Handling Partial Data Mapping]
    Given [S:StoredProcedure: retrieve_similar_nodes_twostep_batch] [P:returns] [O:SQL rows with incomplete column data for some candidate nodes]
    When [S:Function: retrieve_similar_nodes_batch] [P:processes] [O:each SQL result row and detects rows with an unexpected number of columns]
    Then [S:Library: logging] [P:logs] [O:a WARNING event at Level: warning for rows with incomplete data including query_idx details]
    And [S:Function: retrieve_similar_nodes_batch] [P:continues processing] [O:the remaining valid rows ensuring Partial Data Handling Rate ≥ 95%]
    And [S:Variable: similar_nodes_by_query] [P:includes] [O:only valid candidate nodes mapped to each BlueprintStep]
