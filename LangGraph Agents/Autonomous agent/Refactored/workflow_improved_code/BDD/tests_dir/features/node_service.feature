# ======================================================================
# File: ai_workflow_service.feature
# Purpose: Exhaustive BDD matrix for NodeService + Embedding + SQL stack
# Entity tags follow [Type:instance] syntax for every step element.
# ======================================================================

###############################################################################
#  F E A T U R E  1 :  N O D E   F I L T E R I N G   &   S E L E C T I O N    #
###############################################################################
@NodeService
Feature: [Class:NodeService] Accurate and deterministic node selection  
  As a [Role:Developer] operating a [System:AIWorkflowService]  
  I want [Function:filter_nodes_by_embedding_batch] to map every [BlueprintStep]  
  to a correct [Entity:CandidateNode] list or a precise [Entity:MissingNodeReport],  
  So that down-stream [Component:WorkflowPlanner] never dereferences null.  
  KPI: 0 silent failures, deterministic output for identical inputs.

  # ----- HAPPY-PATH ----------------------------------------------------
  @HappyPath
  Scenario: [Story:CompleteSuccess] all blueprint steps resolved to nodes  
    Given a valid [Array:BlueprintStepList] with ≥ 2 items  
      And [Database:PostgreSQL_pgvector] contains matching [Table:AVAILABLE_NODES]  
      And [API:AIService] returns {"SELECTED_NODE": ["node-1","node-2"]} within 500 ms  
    When [Function:filter_nodes_by_embedding_batch] is invoked  
    Then [Return:FilteredNodeMap] has 2 non-empty [List:CandidateNode] entries  
      And [Dictionary:State] lacks key [Flag:missing_node_error]  

  # ----- PROPERTY-BASED (top_k boundaries) ----------------------------
  @PropertyBased
  Scenario Outline: [Story:TopKClamp] top_k value <top_k> limits candidate list  
    Given a valid [Array:BlueprintStepList] with 3 items  
    When [Function:filter_nodes_by_embedding_batch] is invoked with [Integer:<top_k>]  
    Then every [List:CandidateNode] length ≤ <Integer:<top_k>>  
    Examples: | top_k |  
              | 1     |  
              | 10    |  
              | 25    |  

  # ----- EDGE-CASE: duplicate node ids --------------------------------
  @EdgeCase
  Scenario: [Story:DuplicateIDs] duplicate node ids are deduplicated  
    Given [API:AIService] returns {"SELECTED_NODE": ["dup-1","dup-1"]}  
      And the [Database] contains one [Node:id="dup-1"]  
    When [Function:process_blueprint_step] executes  
    Then the resulting [List:CandidateNode] length equals 1  

  # ----- CHAOS: AI returns MISSING_NODE -------------------------------
  # Comment: Covers line 1029 in _invoke_ai: returns [] on "MISSING_NODE" key; coverage tool may not register this line as executed due to suppress context.

  @Chaos
  Scenario: [Story:DeclaredMissingNode] AI explicitly indicates missing node  
    Given [API:AIService] returns {"MISSING_NODE": "true"}  
    When [Function:process_blueprint_step] executes  
    Then [Flag:MissingNode] is true  
      And [List:CandidateNode] is empty  
      And [Dictionary:State] contains [Flag:missing_node_error]  

  @Chaos
  Scenario: [Story:AICallFailure] AI call raises exception and missing node appended
    Given AIService raises an exception during call
    When [Function:filter_nodes_by_embedding_batch] is invoked
    Then [Flag:MissingNode] is true
    And missing node report is generated
    
  # ----- UNEXPECTED: non-deterministic AI order -----------------------
  @Unexpected
  Scenario: [Story:OrderIndependence] candidate order does not affect equality  
    Given two identical calls to [Function:process_blueprint_step]  
      And [API:AIService] returns ids ["a","b"] in run-1 and ["b","a"] in run-2  
    When results are compared  
    Then the two [Return:FilteredNodeMap] objects are set-equal  

  # ----- BOUNDARY: blueprint-step id collision ------------------------
  @Boundary
  Scenario: [Story:StepIdCollision] two steps share identical .step value  
    Given [Array:BlueprintStepList] contains two items with [Field:step]="dup"  
    When [Function:retrieve_similar_nodes_batch] maps results  
    Then the second entry logs "duplicate key" at [Log:WARNING]  
      And merges candidate lists rather than overwriting  

  # ----- MODEL-BASED: READY→FILTERED transition -----------------------
  @ModelBased
  Scenario: [Story:FSMTransition] blueprint step passes through FSM states  
    Given [StateMachine:NodeSelectionFSM] is in READY  
    When [Action:filter_ai_prompt] succeeds  
    Then state is PROMPTED  
    When [Action:parse_ai_response] returns valid ids  
    Then state is FILTERED  

###############################################################################
#  F E A T U R E  2 :  E M B E D D I N G   G E N E R A T I O N               #
###############################################################################
@EmbeddingService
Feature: [Service:EmbeddingService] Stable and bounded embedding generation  
  As a [Role:MLEngineer]  
  I want [Function:compute_normalized_embeddings] to always produce 1024-dim vectors  
  bounded by L2-norm 1, so SQL similarity stays well-defined.  

  @HappyPath
  Scenario: [Story:StandardText] standard ASCII text yields unit-norm vector  
    Given the string "standard text"  
    When [Function:compute_normalized_embeddings] is called  
    Then [Vector:Embedding] length = 1024  
      And L2-norm = 1 ± 1e-6  

  @Fuzz
  Scenario Outline: [Story:UnicodeStress] random unicode in <field> never crashes  
    Given [BlueprintStep] field [Field:<field>] contains 256 random unicode code-points  
    When embeddings are generated  
    Then no [Exception] is raised  
    Examples: | field |  
              | input |  
              | output |  
              | tags |  
              | description |  

  @Boundary
  Scenario: [Story:MaxTokenLength] 8 K token text is truncated gracefully  
    Given a 50 KB string in [Field:description]  
    When embeddings are generated  
    Then [Vector:Embedding] length = 1024  
      And an [Log:INFO] entry notes "input truncated"  

  @Regression
  Scenario: [Story:Deterministic] identical text twice returns identical vector  
    Given the text "idempotent"  
    When embeddings are generated twice  
    Then the two vectors are bit-wise identical  

  @Z3
  Scenario: [Story:NormConstraint] solver proves norm ≤ 1 for any output  
    Given a symbolic [Vector:Embedding] from the generator  
    When [Rule:Z3NormConstraint] is applied  
    Then solver returns SAT  

###############################################################################
#  F E A T U R E  3 :  D A T A B A S E   S I M I L A R I T Y   Q U E R Y     #
###############################################################################
@Database
Feature: [StoredProcedure:retrieve_similar_nodes_twostep_batch] Correct similarity ranking  
  As a [Role:DBA]  
  I need similarity SQL to rank nodes accurately and never corrupt data.  

  @HappyPath
  Scenario: [Story:TopScoreFirst] highest total_score appears first  
    Given formatted embeddings for 3 queries  
      And the DB returns rows with total_score 0.9, 0.7, 0.2  
    When results are parsed  
    Then ordering in [List:CandidateTuple] is 0.9 → 0.7 → 0.2  

  @Boundary
  Scenario: [Story:ZeroRows] stored procedure returns no rows  
    Given [Integer:top_k]=5  
      And DB returns []  
    When mapping runs  
    Then [List:CandidateTuple] is empty  
      And no exception is raised  

  @Unexpected
  Scenario: [Story:ColumnMismatch] row has 7 columns, not 8  
    Given DB returns a 7-column row  
    When [Function:map_sql_results_to_steps] executes  
    Then logs "Unexpected number of columns"  
      And skips the row  

  @Contract
  Scenario: [Story:InvalidQueryIdx] query_idx ≥ length(mapping_keys)  
    Given DB returns query_idx 99 while mapping_keys length = 3  
    When mapping runs  
    Then row is discarded  
      And logs "Invalid query index"  

  @Performance
  Scenario: [Story:PreparedPlan] repeated calls reuse prepared plan  
    Given 100 sequential calls to stored procedure  
    When monitoring [Metric:PlanCacheHits]  
    Then cache hits ≥ 95  

  @LongRun
  Scenario: [Story:ConnectionLeak] 10 000 queries do not leak connections  
    Given pool size = 20  
    When 10 000 queries are executed  
    Then [Metric:OpenConnections] ≤ 20 throughout  

###############################################################################
#  F E A T U R E  4 :  E R R O R   H A N D L I N G   &   L O G G I N G       #
###############################################################################
@Observability
Feature: [Theme:ErrorHandling] All failures are surfaced, logged, and classified  
  As a [Role:SRE]  
  I need every raised exception to be logged with stacktrace and context so MTTR < 5 min.  

  @EdgeCase
  # Comment: Covers lines 1022, 1023 in _invoke_ai: exception handling for AI call failure; coverage tool may not register these lines as executed.
  Scenario: [Story:TemplateErrorBubble] Jinja2 TemplateError is wrapped & re-raised  
    Given [Component:TemplateRenderer] raises [Exception:TemplateError]  
    When [Function:filter_ai_prompt] runs  
    Then outer [Exception] message = "AI prompt construction error"  
      And inner stacktrace contains "TemplateError"  

  @Chaos
  Scenario: [Story:DBConnectionFailure] network disconnection during query  
    Given DB connection is severed mid-transaction  
    When [Function:execute_similarity_query] runs  
    Then function rolls back  
      And logs "SQL query execution failed" at level ERROR  

# Comment: Covers line 1032 in _invoke_ai: raises AIServiceError on invalid JSON; coverage tool may not register this line as executed.
@Unexpected
Scenario: [Story:ParseJSONFail] AIService returns invalid JSON  
  Given [API:AIService] returns "{not-json}"
  When [Function:filter_nodes_by_embedding_batch] executes
  Then returns empty map and one missing node
  And state missing_node_error is true
  And logs "Error parsing AI response"

  # @Unexpected
  # Scenario: [Story:ParseJSONFail] AIService returns invalid JSON  
  #   Given [API:AIService] returns "{not-json}"  
  #   When [Function:parse_ai_response] executes  
  #   Then [Flag:MissingNode] is true  
  #     And logs "Error parsing AI response"  

  @Boundary
  Scenario: [Story:OverflowScores] similarity score > 1 is clamped with warning  
    Given DB returns total_score 1.8  
    When mapping runs  
    Then score is clamped to 1  
      And logs "clamped" at WARNING  

  @Regression
  Scenario: [Story:LogSchema] every ERROR log includes keys [timestamp,level,msg]  
    Given any ERROR event  
    When log formatter emits record  
    Then record JSON has those keys  

###############################################################################
#  F E A T U R E  5 :  P E R F O R M A N C E   &   S C A L A B I L I T Y     #
###############################################################################
@Performance
Feature: [KPI:p95Latency] Service meets latency budget under load  

  @Load
  Scenario: [Story:100QPS] 100 QPS for 5 min keeps p95 ≤ 250 ms  
    Given load generator issues 100 requests/s to [Function:filter_nodes_by_embedding_batch]  
    When 5 minutes elapse  
    Then measured p95 latency ≤ 250 ms  

  @Spike
  Scenario: [Story:TrafficSpike] sudden 10× spike handled by back-pressure  
    Given baseline load 50 QPS  
    When traffic spikes to 500 QPS for 30 s  
    Then no [Exception:ConnectionPoolTimeout] is raised  
      And average latency ≤ 400 ms  

  @Memory
  Scenario: [Story:HighMemDescription] 500 KB description does not OOM  
    Given [BlueprintStep] with 500 KB in [Field:description]  
    When embeddings are generated  
    Then peak [Metric:RSS] increase ≤ 40 MB  

  @Concurrency
  Scenario: [Story:ThreadSafety] 200 threads call compute_normalized_embeddings  
    Given thread pool of 200  
    When each thread processes unique text  
    Then no [Exception:RaceCondition] is raised  
      And results count = 200  

###############################################################################
#  F E A T U R E  6 :  S E C U R I T Y   &   V A L I D A T I O N             #
###############################################################################
@Security
Feature: [Concept:DefenceInDepth] Service resists common injection & misuse  

  @Injection
  Scenario: [Story:SQLInjectionAttempt] malicious description is neutralised  
    Given [Field:description] = "'; DROP TABLE nodes;--"  
    When embeddings are formatted for SQL  
    Then resulting [String:SQLParameter] contains only digits, '.', ',' and '[' ']'  

  @Validation
  Scenario: [Story:NegativeTopK] negative top_k raises ValueError  
    Given [Integer:top_k] = -3  
    When filter_nodes_by_embedding_batch is invoked  
    Then [Exception:ValueError] message contains "top_k must be > 0"  

  @Auth
  Scenario: [Story:APITokenMissing] HF API token env var unset causes auth error  
    Given env var [Env:HF_API_TOKEN] is empty  
    When [Service:EmbeddingService] initialises  
    Then [Exception:AuthenticationError] is raised  

  @Compliance
  Scenario: [Story:PIILeak] description contains email addr; redacted before logging  
    Given description field "contact john@example.com"  
    When error is logged  
    Then output replaces "john@example.com" with "[REDACTED]"  

  @Observability
  Scenario: [Story:AuditTrail] every DB write is accompanied by audit event  
    Given [Function:execute_similarity_query] writes to temp table  
    When commit occurs  
    Then [Log:AUDIT] entry records user, timestamp, rows_written  

###############################################################################
#  F E A T U R E  7 :  C O N F I G U R A T I O N   &   S T A R T U P          #
###############################################################################
@Configuration
Feature: [Component:StartupValidator] Environment & configuration sanity-check  
  As an [Role:Operator]  
  I need the service to validate its configuration at boot so that it fails fast  
  and avoids undefined behaviour in production.  

  @HappyPath
  Scenario: [Story:EnvVarsPresent] all required env vars exist  
    Given env vars [Env:MODEL_USED], [Env:HF_API_TOKEN], [Env:DB_HOST] are set  
    When [Class:StartupValidator] runs at boot  
    Then service enters [State:RUNNING]  

  @EdgeCase
  Scenario: [Story:MissingEnvVar] mandatory env var is absent  
    Given [Env:MODEL_USED] is unset  
    When [Class:StartupValidator] runs  
    Then service exits with [ExitCode:78]  
      And logs "missing env var MODEL_USED" at [Log:ERROR]  

  @Boundary
  Scenario: [Story:InvalidModelPath] LOCAL_MODEL_PATH points to non-existent dir  
    Given [Env:LOCAL_MODEL_PATH] = "/tmp/does/not/exist"  
    When [Class:StartupValidator] checks filesystem  
    Then [Exception:FileNotFoundError] is raised  

  @Reload
  Scenario: [Story:HotReload] config file changed triggers live reload  
    Given service in [State:RUNNING]  
      And [File:/etc/aiwf/config.yaml] is touched  
    When [Component:ConfigWatcher] notices change  
    Then new settings are applied without restart  
      And a [Log:INFO] entry "configuration reloaded" appears  

###############################################################################
#  F E A T U R E  8 :  D E P E N D E N C Y   V E R S I O N   &   C O N T R A C T #
###############################################################################
@Dependency
Feature: [Concept:VersionPinning] Upstream dependency changes are contained  

  @Contract
  Scenario: [Story:EmbeddingModelUpgrade] model hash drift detected  
    Given remote model "BAAI/bge-m4" hash differs from cached copy  
    When [Function:EmbeddingService.download_or_load] runs  
    Then service refuses to start with [Exception:HashMismatchError]  

  @Unexpected
  Scenario: [Story:DBSchemaChange] column added to AVAILABLE_NODES  
    Given DB schema version = 2 while code expects version 1  
    When [Class:NodeService] queries the table  
    Then [Exception:SchemaVersionError] is raised  
      And migration guide path is logged  

  @Chaos
  Scenario: [Story:LLMEndpointVersionBump] AIService adds field "reason"  
    Given AIService response {"SELECTED_NODE":["x"],"reason":"score"}  
    When [Function:parse_ai_response] executes  
    Then unexpected key is ignored  
      And warning logged "unknown key reason"  

###############################################################################
#  F E A T U R E  9 :  S T A T E   S A F E T Y   &   T H R E A D - S A F E T Y #
###############################################################################
@StateSafety
Feature: [Dictionary:State] remains consistent under concurrency  

  @Concurrency
  Scenario: [Story:MissingFlagRace] parallel updates do not clobber flags  
    Given 100 threads each set [Flag:missing_node_error] using [Function:atomic_set]  
    When execution completes  
    Then [Dictionary:State] value is true  
      And no [Exception:RaceCondition] is raised  

  @Boundary
  Scenario: [Story:FlagReset] missing_node_error resets between requests  
    Given previous request sets [Flag:missing_node_error]=true  
    When new request starts  
    Then [Dictionary:State] resets [Flag:missing_node_error] to false  

  @Memory
  Scenario: [Story:LoggerQueueGrowth] logger queue size bound under burst  
    Given 10 000 ERROR logs generated in 1 s  
    When monitoring [Metric:LoggerQueueLength]  
    Then length ≤ 1 000  

###############################################################################
#  F E A T U R E 10 :  A N A L Y T I C S   &   K P I   R E P O R T I N G     #
###############################################################################
@Observability
Feature: [Module:MetricsEmitter] Accurate KPI emission for SLO dashboards  

  @HappyPath
  Scenario: [Story:EmitSuccessMetric] successful call increments success counter  
    Given initial [Metric:node_select_success_total] = N  
    When [Function:filter_nodes_by_embedding_batch] succeeds  
    Then counter = N + 1  

  @EdgeCase
  Scenario: [Story:EmitErrorMetric] error increments failure counter  
    Given initial [Metric:node_select_failure_total] = F  
      And AIService times out  
    When function returns missing_node_error  
    Then counter = F + 1  

  @Performance
  Scenario: [Story:LatencyHistogram] latency recorded in histogram  
    Given call duration = 180 ms  
    When metrics emitted  
    Then [Metric:node_select_latency_seconds_bucket] bucket "0.25" increases by 1  

  @Gauge
  Scenario: [Story:OpenConnectionsGauge] gauge tracks DB connections  
    Given pool opens 5 new connections  
    When metrics scrape occurs  
    Then [Metric:db_open_connections] value reflects increment  

###############################################################################
#  F E A T U R E 11 :  R E C O V E R Y   &   F A I L O V E R                 #
###############################################################################
@Resilience
Feature: [Strategy:GracefulDegradation] Service continues partial operation  

  @Fallback
  Scenario: [Story:CacheFallback] AIService down → heuristic cache used  
    Given AIService returns 5xx  
      And [Cache:NodeHeuristics] has entry for step "classify-image"  
    When [Function:process_blueprint_step] runs  
    Then cached node id is returned  
      And [Log:INFO] "used heuristic cache" appears  

  @CircuitBreaker
  Scenario: [Story:CircuitBreakerTrip] 5 consecutive timeouts open circuit  
    Given AIService times out 5 times within 1 minute  
    When sixth request arrives  
    Then circuit breaker returns error immediately  
      And [Metric:circuit_open] = 1  

  @Retry
  Scenario: [Story:TransientDBError] transient DB error resolved by retry  
    Given first query raises [Exception:TransientError]  
      And retry policy max_attempts = 3  
    When operation retried  
    Then second attempt succeeds  
      And total attempts = 2  

###############################################################################
#  F E A T U R E 12 :  S E C U R I T Y   C O N T I N U E D                   #
###############################################################################
@Security
Feature: [Concept:PIIProtection] Service never logs PII or secrets  

  @Masking
  Scenario: [Story:ApiTokenMask] HF_API_TOKEN masked in logs  
    Given env var HF_API_TOKEN="hf_secret_123"  
    When logger writes an exception containing token  
    Then output shows "****" instead of "hf_secret_123"  

  @GDPR
  Scenario: [Story:RightToErase] user requests deletion of embedding vectors  
    Given user id "abc"  
      And vectors exist in DB  
    When delete API called  
    Then vectors are removed  
      And audit log records deletion  

  @RateLimit
  Scenario: [Story:BruteForceLogin] 50 failed auth attempts triggers lock  
    Given 50 failed HF token validations in 60 s  
    When next request arrives  
    Then [Exception:RateLimitExceeded] is raised  

###############################################################################
#  F E A T U R E 13 :  D E B U G G A B I L I T Y                            #
###############################################################################
@Debug
Feature: [Theme:Traceability] Developers can reproduce any failure within 5 min  

  @TraceID
  Scenario: [Story:PropagateTraceID] every log line contains trace_id  
    Given incoming HTTP header X-Trace-Id="xyz"  
    When request processed  
    Then all logs contain "trace_id":"xyz"  

  @Dump
  Scenario: [Story:OnErrorDump] stacktrace + input snapshot stored on error  
    Given AIService returns invalid JSON  
    When parse_ai_response raises exception  
    Then [File:/tmp/dump/parse_ai_response_xyz.json] is created  
      And file contains offending JSON  

###############################################################################
#  F E A T U R E 14 :  A C C E S S I B I L I T Y   &   I 1 8 N              #
###############################################################################
@Accessibility
Feature: [Concept:I18N] Service handles RTL scripts and emoji gracefully  

  @RTL
  Scenario: [Story:ArabicDescription] Arabic description processed  
    Given description field "وصف"  
    When embeddings generated  
    Then vector length = 1024  

  @Emoji
  Scenario: [Story:EmojiTags] tag list contains emoji  
    Given tags ["📦", "🚀"]  
    When embeddings generated  
    Then no exception raised  

###############################################################################
# End of file
###############################################################################
