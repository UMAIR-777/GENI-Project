# # from prompts.connection import get_connection
# # from prompts.store_procedure import STORE_PROCEDURE_QUERIES

# import os
# import json
# import psycopg2
# from typing import List, Dict, Any, Tuple
# from dataclasses import dataclass
# import logging
# from embedding_service import EmbeddingService
# from psycopg2.pool import ThreadedConnectionPool
# from dotenv import load_dotenv
# from huggingface_hub import InferenceClient
# from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES

# # Configure logging for production quality. Logging should integrate with centralized systems (e.g., ELK, Sentry)
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
# logger = logging.getLogger(__name__)

# # Load environment variables.
# load_dotenv()

# # Create an instance of InferenceClient
# client = InferenceClient(token=os.getenv("HF_TOKEN"))

# # Instantiate the EmbeddingService
# embedding_service = EmbeddingService(client)

# # Global connection pool variable.
# pool: ThreadedConnectionPool = None

# class WorkflowError(Exception):
#     """
#     Custom exception raised for errors in workflow processing.
    
#     This exception is used to indicate critical failures in workflow generation,
#     retrieval, or persistence that might lead to catastrophic outcomes if not handled.
#     """
#     pass

# @dataclass
# class Workflow:
#     """
#     Data class representing a workflow with state, nodes, edges, and missing nodes.

#     @Feature: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
#     @Scenario: Integrity of Workflow JSON Normalization

#     Attributes:
#         state (Dict[str, Any]): The current state of the workflow.
#         nodes (List[Any]): List of workflow nodes.
#         edges (List[Any]): List of connections between nodes.
#         missing_nodes (List[Dict[str, Any]]): List of missing nodes, if any.
#     """
#     state: Dict[str, Any]
#     nodes: List[Any]
#     edges: List[Any]
#     missing_nodes: List[Dict[str, Any]] = None

#     def normalize(self) -> Dict[str, Any]:
#         """
#         Normalize the workflow into a JSON-compatible dictionary ensuring that
#         all keys are present and of the correct type.

#         @Feature: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
#         @Scenario: Integrity of Workflow JSON Normalization

#         Returns:
#             Dict[str, Any]: A normalized workflow dictionary.
#         """
#         normalized = {
#             "state": self.state if isinstance(self.state, dict) else {},
#             "nodes": self.nodes if isinstance(self.nodes, list) else [],
#             "edges": self.edges if isinstance(self.edges, list) else [],
#             "missing_nodes": self.missing_nodes if isinstance(self.missing_nodes, list) else []
#         }
#         return normalized

# # Type alias for workflow retrieval tuple: (id, description, workflow, similarity)
# WorkflowTuple = Tuple[int, str, Workflow, float]

# class DatabaseManager:
#     """
#     Encapsulates database setup and workflow storage/retrieval operations.
#     """
#     def __init__(self, embedding_service):
#         self.embedding_service = embedding_service
#         # ... other initialization code if needed ...

#     def get_db_pool(self) -> ThreadedConnectionPool:
#         """
#         Get the global database connection pool.

#         @Feature: Database Connection Management
#         @Scenario: Provide access to the connection pool

#         Returns:
#             ThreadedConnectionPool: The global connection pool instance.
#         """
#         # global pool
#         return self.pool

#     def load_sql_file(self, file_path: str) -> str:
#         """
#         Load SQL commands from a file.

#         @Feature: Validate Database Setup, SQL Execution, and Resilience to Misconfiguration  
#         @Scenario: Validate Database Setup, SQL Execution, and Resilience to Misconfiguration  

#         Args:
#             file_path (str): Path to the SQL file.

#         Returns:
#             str: Contents of the SQL file as a string.

#         Raises:
#             IOError: If the file cannot be read or is empty.
#         """
#         try:
#             with open(file_path, "r") as f:
#                 sql_commands = f.read()
#             if not sql_commands:
#                 raise ValueError("SQL file is empty.")
#             return sql_commands
#         except Exception as e:
#             logger.error("Error loading SQL file '%s': %s", file_path, e)
#             raise

#     def setup_database(self, sql_file_path: str = None) -> None:
#         """Setup the PostgreSQL database and establish connection pool."""
#         # global pool
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         default_sql_path = os.path.join(current_dir, "DATA_FOLDER", "database_queries.sql")
#         sql_file_path = sql_file_path or default_sql_path

#         # Load SQL commands once
#         try:
#             sql_commands = self.load_sql_file(sql_file_path)
#         except Exception as e:
#             logger.error("Failed to load SQL file: %s", e)
#             raise

#         # Execute database setup
#         conn = None
#         try:
#             conn = psycopg2.connect(
#                 dbname=os.getenv("DB_NAME"),
#                 user=os.getenv("DB_USER"),
#                 password=os.getenv("DB_PASSWORD"),
#                 host=os.getenv("DB_HOST"),
#                 port=os.getenv("DB_PORT"),
#                 sslmode='disable'
#             )

#             with conn.cursor() as cur:
#                 cur.execute(sql_commands)
#             conn.commit()
#             logger.info("Database setup completed successfully.")
#         except Exception as e:
#             if conn:
#                 conn.rollback()
#             if "already exists" in str(e):
#                 logger.info("Database objects already exist. Continuing without error.")
#             else:
#                 logger.error("Database setup execution failed: %s", e)
#                 raise
#         finally:
#             if conn:
#                 conn.close()

#         # Create connection pool
#         try:
#             self.pool = ThreadedConnectionPool(
#                 minconn=1,
#                 maxconn=20,
#                 dbname=os.getenv("DB_NAME"),
#                 user=os.getenv("DB_USER"),
#                 password=os.getenv("DB_PASSWORD"),
#                 host=os.getenv("DB_HOST"),
#                 port=os.getenv("DB_PORT"),
#             )
#             if self.pool:
#                 logger.info("Database connection pool established successfully.")
#         except Exception as e:
#             logger.error("Error creating database connection pool: %s", e)
#             raise

#     def close_connection_pool(self) -> None:
#         """
#         Close all active connections in the database connection pool to ensure proper resource cleanup.

#         @Feature: Validate Robust Error Handling, Dependency Resolution, and Resource Management  
#         @Scenario: Validate Robust Error Handling, Dependency Resolution, and Resource Management  

#         Raises:
#             Exception: If an error occurs during the closure of the connection pool.
#         """
#         # global pool
#         if self.pool:
#             try:
#                 self.pool.closeall()
#                 logger.info("Database connection pool closed successfully.")
#             except Exception as e:
#                 logger.error("Error closing database connection pool: %s", e)
#                 raise

#     def retrieve_similar_workflow(self, query: str, top_k: int = 1, similarity_threshold: float = 0.8) -> List[WorkflowTuple]:
#         """
#         Retrieve workflows similar to the given query by computing vector similarity against stored embeddings.
#         Embedding generation and normalization are performed, and a secure SQL query retrieves workflows
#         exceeding the specified similarity threshold.

#         @Feature: Retrieval of High-Similarity Workflow Under Diverse Input Variations
#         @Scenario: Integrity of Workflow JSON Normalization
#         @Scenario: Robust Error Handling and Exception Safety in Adverse Conditions

#         Args:
#             query (str): A non-empty string representing the user task query.
#             top_k (int): Maximum number of similar workflows to retrieve.
#             similarity_threshold (float): Minimum similarity score threshold.

#         Returns:
#             List[WorkflowTuple]: A list of tuples containing workflow id, description, workflow object, and similarity score.

#         Raises:
#             ValueError: If the query is invalid.
#             WorkflowError: If embedding generation or database retrieval fails.
#         """
#         # Validate input
#         if not isinstance(query, str) or not query.strip():
#             raise ValueError("Query must be a non-empty string.")
        
#         try:
#             # query_embedding = self.embedding_service.get_embeddings(query)
#             # print(query_embedding)
#             query_embedding = self.embedding_service.model.encode(query).tolist()
#             # Ensure we have a flat list
#             if isinstance(query_embedding, list):
#                 # if isinstance(query_embedding[0], list):
#                 #     query_embedding = query_embedding[0]
#                 query_embedding = self.embedding_service.normalize_embedding(query_embedding)
                
#                 query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
#         except Exception as e:
#             logger.error("Error generating query embedding: %s", e)
#             raise WorkflowError("Failed to generate query embedding") from e

#         conn = None
#         try:
#             conn = psycopg2.connect(
#                 dbname=os.getenv("DB_NAME"),
#                 user=os.getenv("DB_USER"),
#                 password=os.getenv("DB_PASSWORD"),
#                 host=os.getenv("DB_HOST"),
#                 port=os.getenv("DB_PORT")
#             )
#             with conn.cursor() as cur:
#                 # Ensure the workflows table exists
#                 cur.execute("""
#                     SELECT EXISTS (
#                         SELECT FROM pg_tables 
#                         WHERE schemaname = 'public' AND tablename = 'workflows'
#                     );
#                 """)
#                 if not cur.fetchone()[0]:
#                     logger.info("Table 'workflows' does not exist; returning empty result.")
#                     return []

#                 sql_query = """
#                     SELECT id, descriptions, workflow, 1 - (embedding <=> %s::vector) AS similarity
#                     FROM workflows
#                     WHERE 1 - (embedding <=> %s::vector) >= %s
#                     ORDER BY similarity DESC
#                     LIMIT %s;
#                 """
#                 cur.execute(sql_query, (query_embedding_str, query_embedding_str, similarity_threshold, top_k))
#                 results = cur.fetchall()
#                 workflows: List[WorkflowTuple] = []
#                                 # Check if we have any results
#                 if not results:
#                     logger.info("No similar workflows found.")
#                     return []
                    
#                 # Process each result
#                 for row in results:
#                     wf_id, desc, wf_data, sim = row
                    
#                     try:
#                         if isinstance(wf_data, str):
#                             wf_data = json.loads(wf_data)
                        
#                         # Extract the main workflow data
#                         main_data = wf_data.get("main", {})
#                         # missing_nodes = wf_data.get("missing_nodes", [])
                        
#                         # Create workflow object with the correct structure
#                         workflow_obj = Workflow(
#                             state=main_data.get("state", {}),
#                             nodes=main_data.get("nodes", []),
#                             edges=main_data.get("edges", []),
#                             # missing_nodes=missing_nodes
#                         )
                        
#                         workflows.append((wf_id, desc, workflow_obj, sim))
#                         logger.info("Retrieved workflow id=%s with similarity=%.4f", wf_id, sim)
                        
#                         # Debug logging
#                         logger.debug("Workflow data: %s", json.dumps(wf_data, indent=2))
#                     except json.JSONDecodeError as je:
#                         logger.error("Error parsing workflow JSON for id=%s: %s", wf_id, je)
#                         continue
#                     except Exception as e:
#                         logger.error("Error processing workflow id=%s: %s", wf_id, e)
#                         continue    
                
#                 return workflows
#         except Exception as e:
#             logger.error("Error retrieving similar workflows: %s", e)
#             raise WorkflowError("Database query failed") from e
#         finally:
#             if conn:
#                 conn.close()

#     def initialize_node_store(self) -> None:
#         """One-time initialization of node store with embeddings."""
#         try:
#             # Check if nodes are already stored
#             with self.get_connection() as conn:
#                 with conn.cursor() as cur:
#                     cur.execute("SELECT COUNT(*) FROM nodes")
#                     if cur.fetchone()[0] > 0:
#                         logger.info("Nodes already initialized in database")
#                         return

#             # Store nodes and their embeddings
#             self.store_nodes_with_embeddings(AVAILABLE_NODES)
#             logger.info("Successfully initialized node store")
#         except Exception as e:
#             logger.error(f"Node store initialization failed: {e}")
#             raise

#     def save_workflow(self, descriptions: str, workflow_json: str, missing_nodes: List[Dict[str, Any]] = None) -> None:
#         """
#         Save the workflow into the database along with its embedding. This function validates inputs,
#         normalizes the workflow JSON, and performs a secure database transaction to insert the workflow record.
#         It also handles potential issues such as missing tables or connectivity errors robustly.

#         @Feature: Robust Error Handling and Exception Safety in Adverse Conditions
#         @Scenario: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
#         @Scenario: Compliance with SOLID Principles and High-Quality Code Standards

#         Args:
#             descriptions (str): A non-empty string describing the workflow.
#             workflow_json (str): The normalized workflow JSON string.
#             missing_nodes (List[Dict[str, Any]], optional): List of missing nodes; defaults to an empty list.

#         Raises:
#             ValueError: If descriptions or workflow_json are invalid.
#             WorkflowError: If embedding generation or database insertion fails.
#         """
#         if not isinstance(descriptions, str) or not descriptions.strip():
#             raise ValueError("Descriptions must be a valid non-empty string.")
#         if not isinstance(workflow_json, str) or not workflow_json.strip():
#             raise ValueError("Workflow JSON must be a valid non-empty string.")

#         # Merge missing nodes into the workflow JSON.
#         workflow_dict = json.loads(workflow_json)
#         # workflow_dict["missing_nodes"] = missing_nodes if missing_nodes is not None else []
#         if "missing_nodes" in workflow_dict:
#             del workflow_dict["missing_nodes"]
#         workflow_json = json.dumps(workflow_dict)

#         try:
#             embedding = self.embedding_service.get_embeddings(descriptions)
#             embedding = self.embedding_service.normalize_embedding(embedding)
#             embedding_str = '[' + ','.join(map(str, embedding)) + ']'
#         except Exception as e:
#             logger.error("Error processing embedding for descriptions: %s", e)
#             raise WorkflowError("Embedding generation/normalization failed") from e

#         conn = None
#         try:
#             conn = psycopg2.connect(
#                 dbname=os.getenv("DB_NAME"),
#                 user=os.getenv("DB_USER"),
#                 password=os.getenv("DB_PASSWORD"),
#                 host=os.getenv("DB_HOST"),
#                 port=os.getenv("DB_PORT"),

#             )
#             with conn.cursor() as cur:
#                 sql_insert = """
#                     INSERT INTO workflows (descriptions, workflow, embedding)
#                     VALUES (%s, %s, %s)
#                 """
#                 cur.execute(sql_insert, (descriptions.strip(), workflow_json, embedding_str))
#                 conn.commit()
#                 logger.info("Workflow saved successfully with description: %s", descriptions.strip())
#         except psycopg2.Error as e:
#             if e.pgcode == '42P01':
#                 logger.info("Table 'workflows' does not exist; skipping workflow save.")
#             else:
#                 logger.error("Database insert failed: %s", e)
#                 raise WorkflowError("Database insert failed") from e
#         finally:
#             if conn:
#                 conn.close()


import os
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional, Generator
from psycopg2 import connect, OperationalError, ProgrammingError, Error as PsycopgError
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
from embedding_service import EmbeddingService
from huggingface_hub import InferenceClient
from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES

# Configure structured, production-ready logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Types and common components
PoolType = ThreadedConnectionPool

class WorkflowError(Exception):
    """
    Custom exception for workflow management failures.
    """
    pass

@dataclass
class Workflow:
    state: Dict[str, Any]
    nodes: List[Any]
    edges: List[Any]
    missing_nodes: List[Dict[str, Any]] = None

    def normalize(self) -> Dict[str, Any]:
        """
        @Feature NormalizeWorkflow
        @Scenario HappyPath:AllTypesValid
        @Scenario EdgeCase:NoneValues
        @Scenario EdgeCase:WrongTypes
        Returns a dict ensuring safe types.
        """
        return {
            "state": self.state if isinstance(self.state, dict) else {},
            "nodes": self.nodes if isinstance(self.nodes, list) else [],
            "edges": self.edges if isinstance(self.edges, list) else [],
            "missing_nodes": self.missing_nodes if isinstance(self.missing_nodes, list) else []
        }

class DatabaseManager:
    """
    Encapsulates database setup and workflow CRUD operations.
    Dependencies are injected via constructor (pool & embedding_service).
    """
    def __init__(
        self,
        embedding_service: EmbeddingService,
        db_pool: PoolType = None
    ):
        self.embedding_service = embedding_service
        self.pool = db_pool

    def load_sql_file(self, file_path: str) -> str:
        """
        @Feature SQLLoad
        @Scenario HappyPath:ValidFile
        @Scenario ErrorCase:MissingFile
        @Scenario ErrorCase:EmptyFile
        Loads and returns SQL from given file_path. Raises FileNotFoundError or ValueError.
        """
        if not os.path.isfile(file_path):
            logger.error("SQL file not found: %s", file_path)
            raise FileNotFoundError(f"SQL file {file_path} not found.")
        content = ''
        with open(file_path, 'r', encoding='utf-8') as f:
            # streaming read for large files
            for chunk in iter(lambda: f.read(8192), ''):
                content += chunk
        if not content.strip():
            logger.error("SQL file is empty: %s", file_path)
            raise ValueError("SQL file is empty.")
        return content

    def setup_database(self, sql_file_path: Optional[str] = None) -> None:
        """
        @Feature SetupDB
        @Scenario HappyPath:DefaultSQL
        @Scenario ErrorCase:OverrideSQL
        @Scenario Idempotent:ExistingObjects
        @Scenario ErrorCase:InvalidSQL
        @Scenario ErrorCase:ConnectionFailure
        @Scenario ErrorCase:EnvMissing
        Initializes DB schema and configures connection pool.
        """
        # Determine SQL file path
        base = os.path.dirname(os.path.abspath(__file__))
        path = sql_file_path or os.path.join(base, 'DATA_FOLDER', 'database_queries.sql')
        sql = self.load_sql_file(path)

        # Execute DDL
        conn = None
        try:
            conn = connect(
                dbname=os.getenv('DB_NAME'),
                user=os.environ['DB_USER'],
                password=os.environ['DB_PASSWORD'],
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                sslmode='disable'
            )
            with conn, conn.cursor() as cur:
                cur.execute(sql)
            logger.info("Database schema created.")
        except KeyError as ke:
            logger.error("Missing DB credential: %s", ke)
            raise
        except ProgrammingError as pe:
            msg = str(pe)
            if 'already exists' in msg:
                logger.info("Schema already exists. Skipping DDL.")
            else:
                logger.error("DDL execution failed: %s", pe)
                raise
        except OperationalError as oe:
            logger.error("DB connection/setup error: %s", oe)
            raise
        finally:
            if conn is not None:
                conn.close()

        # Validate pool configuration
        if not self.pool:
            try: 
                self.pool = ThreadedConnectionPool( 
                    minconn=1,
                    maxconn=20,
                    dbname=os.getenv('DB_NAME'),
                    user=os.environ['DB_USER'],
                    password=os.environ['DB_PASSWORD'],
                    host=os.getenv('DB_HOST'),
                    port=os.getenv('DB_PORT')
                )
                logger.info("Connection pool established.") 
            except Exception as e:
                logger.error("Pool creation error: %s", e) 
                raise 

    def get_connection(self) -> Any:
        """
        Retrieves a connection from the pool.
        """
        return self.pool.getconn()

    def get_db_pool(self) -> ThreadedConnectionPool:
        """
        Get the database connection pool.

        @Feature: Database Connection Management
        @Scenario: Provide access to the connection pool

        Returns:
            ThreadedConnectionPool: The global connection pool instance.
        """
        return self.pool # find and check how to get coverage for this line using test
    
    def store_nodes_with_embeddings(self, nodes: List[Dict[str, Any]]) -> None:
        """
        Store nodes with their embeddings in the database.
        
        Args:
            nodes: List of node dictionaries containing node information
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                for node in nodes:
                    embedding = self.embedding_service.get_embeddings(str(node))
                    embedding = self.embedding_service.normalize_embedding(embedding)
                    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                    
                    cur.execute(
                        "INSERT INTO nodes (node_data, embedding) VALUES (%s, %s)",
                        (json.dumps(node), embedding_str)
                    )
                conn.commit()
        except Exception as e:
            logger.error("Failed to store nodes: %s", e)
            raise WorkflowError("Node storage failed") from e
        finally:
            self.close_connection(conn)

    def close_connection(self, conn: Any) -> None:
        """
        Returns a connection to the pool.
        """
        self.pool.putconn(conn)

    def close_pool(self) -> None:
        """
        @Feature ConnectionPoolMgmt
        @Scenario HappyPath:ClosePool
        @Scenario ErrorCase:PoolCloseFailure
        Closes all connections in the pool.
        """
        try:
            self.pool.closeall()
            logger.info("Connection pool closed.")
        except Exception as e:
            logger.error("Error closing pool: %s", e)
            raise

    def retrieve_similar_workflow(
        self,
        query: str,
        top_k: int = 1,
        similarity_threshold: float = 0.8
    ) -> List[Tuple[int, str, Workflow, float]]:
        """
        @Feature SearchWorkflow
        @Scenario HappyPath:MatchFound
        @Scenario ErrorCase:EmptyQuery
        @Scenario EdgeCase:BelowThreshold
        @Scenario ErrorCase:TableMissing
        @Scenario ErrorCase:BadJSON
        @Scenario Chaos:EmbeddingTimeout
        @Scenario BeyondBoundary:HighTopK
        Returns workflows matching the query embedding.
        """
        if not isinstance(query, str) or not query.strip():
            logger.error("Empty query.")
            raise ValueError("Query must be non-empty string.")

        try:
            emb = self.embedding_service.get_embeddings(query)
            emb = self.embedding_service.normalize_embedding(emb)
        except Exception as e:
            logger.error("Embedding error: %s", e)
            raise WorkflowError("Failed to generate query embedding") from e

        conn = self.get_connection()
        results: List[Tuple[int, str, Workflow, float]] = []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='workflows')"
                )
                if not cur.fetchone()[0]:
                    logger.info("workflows table missing.")
                    return []
                sql = (
                    "SELECT id, descriptions, workflow, "
                    "1 - (embedding <=> %s::vector) AS similarity "
                    "FROM workflows "
                    "WHERE 1 - (embedding <=> %s::vector) >= %s "
                    "ORDER BY similarity DESC LIMIT %s"
                )
                limit = min(top_k, self.pool.maxconn)
                emb_str = '[' + ','.join(map(str, emb)) + ']'
                cur.execute(sql, (emb_str, emb_str, similarity_threshold, limit))
                for wid, desc, wf_json, sim in cur.fetchall():
                    try:
                        if isinstance(wf_json, str):
                            data = json.loads(wf_json)
                        else:
                            data = wf_json
                        main = data.get('main', {})
                        wf = Workflow(
                            state=main.get('state', {}),
                            nodes=main.get('nodes', []),
                            edges=main.get('edges', []),
                            missing_nodes=[]
                        )
                        results.append((wid, desc, wf, sim))
                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON for id=%s", wid)
                        continue
        except PsycopgError as e:
            logger.error("DB error: %s", e)
            raise WorkflowError("Database query failed") from e
        finally:
            self.close_connection(conn)

        return results

    def initialize_node_store(self) -> None:
        """
        @Feature NodeStoreInit
        @Scenario HappyPath:FirstInit
        @Scenario Idempotent:AlreadyInit
        @Scenario ErrorCase:CountQueryFailure
        @Scenario ErrorCase:StoreFailure
        Populates AVAILABLE_NODES embeddings if none exist.
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM nodes")
                count = cur.fetchone()[0]
            if count > 0:
                logger.info("Nodes already initialized.")
                return
            self.store_nodes_with_embeddings(AVAILABLE_NODES)
            logger.info("Node store initialized.")
        except Exception as e:
            logger.error("Node store init failed: %s", e)
            raise WorkflowError("Node store initialization failed") from e
        finally:
            self.close_connection(conn)

    def save_workflow(
        self,
        descriptions: str,
        workflow_json: str,
        missing_nodes: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        @Feature PersistWorkflow
        @Scenario HappyPath:ValidSave
        @Scenario ErrorCase:BlankDescription
        @Scenario ErrorCase:InvalidJSON
        @Scenario ErrorCase:TableMissing
        @Scenario ErrorCase:EmbeddingFailure
        @Scenario EdgeCase:MissingNodesField
        @Scenario Chaos:DBInsertFailure
        Persists a new workflow with embedding.
        """
        if not descriptions.strip():
            logger.error("Blank description.")
            raise ValueError("Descriptions must be non-empty.")

        try:
            wf_dict = json.loads(workflow_json)
        except json.JSONDecodeError as je:
            logger.error("Invalid JSON: %s", je)
            raise ValueError("Workflow JSON must be valid.")
        wf_dict.pop('missing_nodes', None)
        clean_json = json.dumps(wf_dict)

        try:
            emb = self.embedding_service.get_embeddings(descriptions)
            emb = self.embedding_service.normalize_embedding(emb)
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            raise WorkflowError("Embedding normalization failed") from e

        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO workflows (descriptions, workflow, embedding) VALUES (%s, %s, %s)",
                    (descriptions.strip(), clean_json, '[' + ','.join(map(str, emb)) + ']')
                )
                conn.commit()
            logger.info("Workflow persisted: %s", descriptions)
        except PsycopgError as e:
            if getattr(e, 'pgcode', '') == '42P01':
                logger.info("Table missing; skipping save.")
            else:
                logger.error("Insert failed: %s", e)
                raise WorkflowError("Database insert failed") from e
            self.close_connection(conn)
