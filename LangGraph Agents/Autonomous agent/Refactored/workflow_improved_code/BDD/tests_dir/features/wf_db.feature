Feature: [Class:DatabaseManager] Load SQL File [Story:SQLLoad] so that [KPI:SQLLoadSuccessRate]
  Scenario: [HappyPath:ValidFile] load_sql_file reads non-empty SQL
    Given the [File:valid.sql] exists with SQL statements
    When the [Function:load_sql_file] is called with "valid.sql"
    Then it returns the file content as [DataType:String]
    And no exception is thrown

  Scenario: [ErrorCase:MissingFile] load_sql_file with nonexistent file
    Given the [File:missing.sql] does not exist
    When the [Function:load_sql_file] is called with "missing.sql"
    Then a [Exception:FileNotFoundError] is raised

  Scenario: [ErrorCase:EmptyFile] load_sql_file with empty file
    Given the [File:empty.sql] exists but is empty
    When the [Function:load_sql_file] is called with "empty.sql"
    Then a [Exception:ValueError] is raised with message "SQL file is empty."
    And the [Component:logger] logs an ERROR

Feature: [Class:DatabaseManager] Setup Database [Story:SetupDB] so that [KPI:SetupSuccessRate]
  Scenario: [HappyPath:DefaultSQL] setup_database with default SQL path
    Given environment variables for DB are set
    And the [File:database_queries.sql] contains valid DDL
    When the [Function:setup_database] is executed
    Then the [Database:PostgreSQL] objects are created
    And the [Component:logger] logs success at INFO

  Scenario: [ErrorCase:OverrideSQL] setup_database with custom SQL path
    Given [File:custom.sql] exists with valid SQL
    When the [Function:setup_database] is called with sql_file_path="custom.sql"
    Then the [Database:PostgreSQL] objects are created using custom.sql

  Scenario: [Idempotent:ExistingObjects] setup_database when tables already exist
    Given the [Database:PostgreSQL] public schema contains target tables
    When the [Function:setup_database] is executed
    Then no exception is thrown
    And the [Component:logger] logs "Database objects already exist. Continuing without error."

  Scenario: [ErrorCase:InvalidSQL] setup_database with malformed SQL
    Given [File:bad.sql] contains invalid SQL statement
    When the [Function:setup_database] is executed
    Then a [Exception:ProgrammingError] is raised
    And the transaction is rolled back
    And the [Component:logger] logs an ERROR

  Scenario: [ErrorCase:ConnectionFailure] setup_database cannot connect
    Given DB_HOST is unreachable
    When the [Function:setup_database] is executed
    Then a [Exception:OperationalError] is raised
    And the [Component:logger] logs an ERROR

  Scenario: [ErrorCase:EnvMissing] setup_database without DB credentials
    Given [EnvVar:DB_USER] or [EnvVar:DB_PASSWORD] is not set
    When the [Function:setup_database] is executed
    Then a [Exception:KeyError] is raised
    And the [Component:logger] logs "DB credentials missing."

Feature: [Component:DatabaseManager] Connection Pool Management [Story:PoolMgmt] so that [KPI:PoolStability]
  Scenario: [HappyPath:CreatePool] create ThreadedConnectionPool
    Given the DB is reachable
    When the [Function:setup_database] has run
    Then the [Component:ThreadedConnectionPool] is instantiated with minconn=1,maxconn=20

  Scenario: [Function:get_db_pool] returns existing pool
    Given the [Component:ThreadedConnectionPool] exists
    When the [Function:get_db_pool] is called
    Then it returns the pool instance

  Scenario: [ErrorCase:NoPool] get_db_pool when pool is None
    Given the [Component:ThreadedConnectionPool] is None
    When the [Function:get_db_pool] is called
    Then it returns None without exception

  Scenario: [HappyPath:ClosePool] close_connection_pool cleans up
    Given the [Component:ThreadedConnectionPool] has active connections
    When the [Function:close_connection_pool] is called
    Then all connections are closed
    And the [Component:logger] logs success at INFO

  Scenario: [ErrorCase:PoolCloseFailure] close_connection_pool throws error
    Given the [Component:ThreadedConnectionPool] closeall() raises Exception
    When the [Function:close_connection_pool] is called
    Then the exception is propagated
    And the [Component:logger] logs an ERROR

Feature: [Class:DatabaseManager] Initialize Node Store [Story:NodeStoreInit] so that [KPI:NodeInitRate]
  Scenario: [HappyPath:FirstInit] initialize_node_store with empty nodes table
    Given the [Database:nodes Table] has zero rows
    When the [Function:initialize_node_store] is executed
    Then [Function:store_nodes_with_embeddings] is called with AVAILABLE_NODES
    And the [Component:logger] logs "Successfully initialized node store"

  Scenario: [Idempotent:AlreadyInit] initialize_node_store when nodes exist
    Given the [Database:nodes Table] has rows (>0)
    When the [Function:initialize_node_store] is executed
    Then no store_nodes_with_embeddings call is made
    And the [Component:logger] logs "Nodes already initialized in database"

  Scenario: [ErrorCase:CountQueryFailure] initialize_node_store count query fails
    Given the COUNT(*) query on nodes table raises Exception
    When the [Function:initialize_node_store] is executed
    Then the exception is propagated as WorkflowError
    And the [Component:logger] logs an ERROR

  Scenario: [ErrorCase:StoreFailure] initialize_node_store store fails
    Given [Function:store_nodes_with_embeddings] raises Exception
    When the [Function:initialize_node_store] is executed
    Then a [Exception:WorkflowError] is raised
    And the [Component:logger] logs an ERROR

Feature: [Component:DatabaseManager] Retrieve Similar Workflow [Story:SearchWorkflow] so that [KPI:SearchAccuracy]
  Scenario: [HappyPath:MatchFound] valid query returns workflow
    Given [Parameter:query] is "find workflow"
    And the [Component:EmbeddingService] returns normalized embedding
    And the [Database:workflows Table] exists with matching embeddings
    When the [Function:retrieve_similar_workflow] is called with query and top_k=1
    Then it returns a list with one [DataType:WorkflowTuple]
    And each tuple contains [Class:Workflow] with normalized fields

  Scenario: [ErrorCase:EmptyQuery] retrieve_similar_workflow with blank query
    Given [Parameter:query] is ""
    When the [Function:retrieve_similar_workflow] is called
    Then a [Exception:ValueError] is raised with message "Query must be a non-empty string."

  Scenario: [EdgeCase:BelowThreshold] no workflows meet similarity threshold
    Given [Parameter:similarity_threshold] is 0.99
    And no rows satisfy threshold
    When retrieve_similar_workflow is called
    Then it returns an empty list
    And the [Component:logger] logs "No similar workflows found."

  Scenario: [ErrorCase:TableMissing] workflows table absent
    Given the [Database:workflows Table] does not exist
    When retrieve_similar_workflow is called
    Then it returns an empty list
    And the [Component:logger] logs table-missing INFO

  Scenario: [ErrorCase:BadJSON] malformed JSON in DB row
    Given the [Column:workflow] contains invalid JSON
    When retrieve_similar_workflow processes the row
    Then the row is skipped without raising
    And the [Component:logger] logs a JSON decode ERROR

  Scenario: [Chaos:EmbeddingTimeout] embedding service timeout
    Given the [Component:EmbeddingService] raises TimeoutError
    When retrieve_similar_workflow is called
    Then a [Exception:WorkflowError] is raised with message "Failed to generate query embedding"
    And the [Component:logger] logs an ERROR

Feature: [Component:DatabaseManager] Save Workflow [Story:PersistWorkflow] so that [KPI:SaveSuccessRate]
  Scenario: [HappyPath:ValidSave] save_workflow inserts row
    Given [Parameter:descriptions] is "new workflow"
    And [Parameter:workflow_json] is valid JSON
    And the [Component:EmbeddingService] returns normalized embedding
    When save_workflow is called
    Then a new row is inserted into [Table:workflows]
    And the [Component:logger] logs success at INFO

  Scenario: [ErrorCase:BlankDescription] descriptions blank
    Given [Parameter:descriptions] is "   "
    When save_workflow is called
    Then a [Exception:ValueError] is raised with message "Descriptions must be a valid non-empty string."

  Scenario: [ErrorCase:InvalidJSON] malformed workflow JSON
    Given [Parameter:workflow_json] is "{invalid"
    When save_workflow is called
    Then a [Exception:ValueError] is raised for JSON parsing
    And the [Component:logger] logs an ERROR

  Scenario: [ErrorCase:TableMissing] workflows table absent
    Given the [Database:workflows Table] does not exist
    When save_workflow is called
    Then no exception propagates for pgcode '42P01'
    And the [Component:logger] logs skipping INFO

  Scenario: [ErrorCase:EmbeddingFailure] embedding generation error
    Given the [Component:EmbeddingService] raises RuntimeError
    When save_workflow is called
    Then a [Exception:WorkflowError] is raised
    And the [Component:logger] logs an ERROR

  Scenario: [EdgeCase:MissingNodesField] workflow_json contains missing_nodes
    Given [Parameter:workflow_json] includes a "missing_nodes" field
    When save_workflow is called
    Then the "missing_nodes" field is removed before insert
    And the row is saved successfully

  Scenario: [Chaos:DBInsertFailure] DB insert error other than '42P01'
    Given psycopg2 insert raises Error with pgcode != '42P01'
    When save_workflow is called
    Then a [Exception:WorkflowError] is raised
    And the [Component:logger] logs an ERROR

Feature: [Class:Workflow] Normalize Workflow Object [Story:Normalize] so that [KPI:NormalizeAccuracy]
  Scenario: [HappyPath:AllTypesValid] normalize with proper types
    Given a [Class:Workflow] instance with dict state, list nodes, list edges, list missing_nodes
    When the [Method:normalize] is called
    Then it returns a dict with same values

  Scenario: [EdgeCase:NoneValues] normalize with None for optional fields
    Given a [Class:Workflow] instance with missing_nodes=None
    When normalize is called
    Then "missing_nodes" in output is an empty list

  Scenario: [EdgeCase:WrongTypes] normalize with wrong types
    Given a Workflow with state as string, nodes as dict, edges as int
    When normalize is called
    Then state, nodes, edges are coerced to {}, [], [] respectively

  Scenario: [HappyPath:ExtraFields] normalize ignores extra attributes
    Given a Workflow instance with additional attributes beyond defined fields
    When normalize is called
    Then only state, nodes, edges, missing_nodes keys appear in output
