# from prompts.connection import get_connection
# from prompts.store_procedure import STORE_PROCEDURE_QUERIES

from email import errors
import os
import json
import uuid
import psycopg2
from typing import List, Dict, Any, Tuple
from typing import NamedTuple, List, Any, Dict
from dataclasses import dataclass
import logging
from .embedding_service import EmbeddingService#
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from .connection import get_connection#

# Configure logging for production quality. Logging should integrate with centralized systems (e.g., ELK, Sentry)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables.
load_dotenv()

# Create an instance of InferenceClient (replace with actual initialization)
# client = InferenceClient()

# Instantiate the EmbeddingService
# embedding_service = EmbeddingService(client)

# Global connection pool variable.
pool: ThreadedConnectionPool = None

class WorkflowError(Exception):
    """
    Custom exception raised for errors in workflow processing.
    
    This exception is used to indicate critical failures in workflow generation,
    retrieval, or persistence that might lead to catastrophic outcomes if not handled.
    """
    pass

@dataclass
class WorkflowRecord(NamedTuple):
    id: str
    name: str
    tenant_id: str
    user_id: str
    group_id: str
    descriptions: str
    workflow: Dict[str, Any]
    similarity: float
    is_public: bool
    version: str
    created_at: str
    updated_at: str

@dataclass
class Workflow:
    """
    Data class representing a workflow with state, nodes, edges, and missing nodes.

    @Feature: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
    @Scenario: Integrity of Workflow JSON Normalization

    Attributes:
        state (Dict[str, Any]): The current state of the workflow.
        nodes (List[Any]): List of workflow nodes.
        edges (List[Any]): List of connectionsf between nodes.
        missing_nodes (List[Dict[str, Any]]): List of missing nodes, if any.
    """
    state: Dict[str, Any]
    nodes: List[Any]
    edges: List[Any]
    missing_nodes: List[Dict[str, Any]] = None

    def normalize(self) -> Dict[str, Any]:
        """
        Normalize the workflow into a JSON-compatible dictionary ensuring that
        all keys are present and of the correct type.

        @Feature: Boundary Condition Testing for Workflow JSON Normalization and Schema Enforcement
        @Scenario: Integrity of Workflow JSON Normalization

        Returns:
            Dict[str, Any]: A normalized workflow dictionary.
        """
        normalized = {
            "state": self.state if isinstance(self.state, dict) else {},
            "nodes": self.nodes if isinstance(self.nodes, list) else [],
            "edges": self.edges if isinstance(self.edges, list) else [],
            "missing_nodes": self.missing_nodes if isinstance(self.missing_nodes, list) else []
        }
        return normalized

# Type alias for workflow retrieval tuple: (id, description, workflow, similarity)
WorkflowTuple = Tuple[int, str, Workflow, float]

class DatabaseManager:
    """
    Encapsulates database setup and workflow storage/retrieval operations.
    """
    def __init__(self, embedding_service):
        self.embedding_service = EmbeddingService()
        # ... other initialization code if needed ...

    def get_db_pool(self) -> ThreadedConnectionPool:
        """
        Get the global database connection pool.

        @Feature: Database Connection Management
        @Scenario: Provide access to the connection pool

        Returns:
            ThreadedConnectionPool: The global connection pool instance.
        """
        # global pool
        return self.pool

    def load_sql_file(self, file_path: str) -> str:
        """
        Load SQL commands from a file.

        @Feature: Validate Database Setup, SQL Execution, and Resilience to Misconfiguration  
        @Scenario: Validate Database Setup, SQL Execution, and Resilience to Misconfiguration  

        Args:
            file_path (str): Path to the SQL file.

        Returns:
            str: Contents of the SQL file as a string.

        Raises:
            IOError: If the file cannot be read or is empty.
        """
        try:
            with open(file_path, "r") as f:
                sql_commands = f.read()
            if not sql_commands:
                raise ValueError("SQL file is empty.")
            return sql_commands
        except Exception as e:
            logger.error("Error loading SQL file '%s': %s", file_path, e)
            raise

    def setup_database(self, sql_file_path: str = None) -> None:
        """Setup the PostgreSQL database and establish connection pool."""
        # global pool
        current_dir = os.path.dirname(os.path.abspath(__file__))
        default_sql_path = os.path.join(current_dir, "DATA_FOLDER", "database_queries.sql")
        sql_file_path = sql_file_path or default_sql_path

        # Load SQL commands once
        try:
            sql_commands = self.load_sql_file(sql_file_path)
        except Exception as e:
            logger.error("Failed to load SQL file: %s", e)
            raise

        # Execute database setup
        conn = None
        try:
            conn = get_connection()

            with conn.cursor() as cur:
                cur.execute(sql_commands)
            conn.commit()
            logger.info("Database setup completed successfully.")
        except Exception as e:
            if conn:
                conn.rollback()
            if "already exists" in str(e):
                logger.info("Database objects already exist. Continuing without error.")
            else:
                logger.error("Database setup execution failed: %s", e)
                raise
        finally:
            if conn:
                conn.close()

        # Create connection pool
        try:
            self.pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
            )
            if self.pool:
                logger.info("Database connection pool established successfully.")
        except Exception as e:
            logger.error("Error creating database connection pool: %s", e)
            raise

            

    def close_connection_pool(self) -> None:
        """
        Close all active connections in the database connection pool to ensure proper resource cleanup.

        @Feature: Validate Robust Error Handling, Dependency Resolution, and Resource Management  
        @Scenario: Validate Robust Error Handling, Dependency Resolution, and Resource Management  

        Raises:
            Exception: If an error occurs during the closure of the connection pool.
        """
        # global pool
        if self.pool:
            try:
                self.pool.closeall()
                logger.info("Database connection pool closed successfully.")
            except Exception as e:
                logger.error("Error closing database connection pool: %s", e)
                raise

    def fetch_nodes(self) -> List[Dict]:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id , input, output, tags, description, spo, node_metadata, created_at, updated_at FROM nodes;"
            )
            rows = cur.fetchall()

        nodes = []
        for node_id, inp, outp, tags, desc, spo_json, meta_json, c_at, u_at in rows:
            spo = spo_json if isinstance(spo_json, dict) else json.loads(spo_json)
            metadata = meta_json if isinstance(meta_json, dict) else json.loads(meta_json)
            nodes.append({
                'id': node_id,
                'input': inp,
                'output': outp,
                'tags': tags,
                'description': desc,
                'spo': spo,
                'node_metadata': metadata,
                'created_at': c_at.isoformat() if u_at else None,
                'updated_at': u_at.isoformat() if u_at else None
            })
        return nodes
    
    def retrieve_similar_workflow(
        self,
        query: str,
        top_k: int = 1,
        similarity_threshold: float = 0.8
    ) -> List[Dict]:
        """
        Returns a list of dicts, each containing all the workflow fields plus 'similarity'.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string.")
        # 1) Embed + normalize
        try:
            raw_emb = self.embedding_service.embed_texts(texts=[query])
            print(f"raw_emb_______________________________:{raw_emb}")
            
            norm_emb = self.embedding_service.normalize_embedding(raw_emb)
            print(f"norm_emb_______________________________:{norm_emb}")
            # print(len(norm_emb))
            # print(len(norm_emb[0]))
            query_embedding_str = "[" + ",".join(f"{x:.6f}" for x in norm_emb[0]) + "]"
            print(f"query_embedding_str_______________________________:{query_embedding_str}")
        except Exception as e:
            logger.error("Error generating query embedding: %s", e)
            raise WorkflowError("Failed to generate query embedding") from e
        
        sql = """
                SELECT
                    id,
                    name,
                    tenant_id,
                    data, 
                    1 - (embedding <=> %s::vector) AS similarity,
                    is_public,
                    version,
                    to_char(created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at,
                    to_char(updated_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS updated_at
                FROM workflows
                WHERE 1 - (embedding <=> %s::vector) >= %s
                ORDER BY similarity DESC
                LIMIT %s;
            """

        results: List[Dict] = []
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(sql, (
                    query_embedding_str,
                    query_embedding_str,
                    similarity_threshold,
                    top_k
                ))
                for (
                    wf_id,
                    name,
                    tenant_id,
                    user_id,
                    group_id,
                    desc,
                    wf_json,
                    sim,
                    is_public,
                    version,
                    c_at,
                    u_at
                ) in cur.fetchall():
                    # ensure we have a Python dict for the JSONB
                    workflow_obj = wf_json if isinstance(wf_json, dict) else json.loads(wf_json)
                    results.append({
                        "id":             wf_id,
                        "name":           name,
                        "tenant_id":      tenant_id,
                        "user_id":        user_id,
                        "group_id":       group_id,
                        "descriptions":   desc,
                        "workflow":       workflow_obj,
                        "similarity":     sim,
                        "is_public":      is_public,
                        "version":        version,
                        "created_at":     c_at,
                        "updated_at":     u_at,
                    })
        except Exception as e:
            logger.error("Error retrieving similar workflows: %s", e, exc_info=True)
            raise WorkflowError("Database query failed") from e
        finally:
            if conn:
                conn.close()

        return results
    

    
    # def retrieve_similar_workflow(self, query: str, top_k: int = 1, similarity_threshold: float = 0.8) -> List[WorkflowTuple]:
    #     """
    #     Retrieve workflows similar to the given query by computing vector similarity against stored embeddings.
    #     Embedding generation and normalization are performed, and a secure SQL query retrieves workflows
    #     exceeding the specified similarity threshold.

    #     @Feature: Retrieval of High-Similarity Workflow Under Diverse Input Variations
    #     @Scenario: Integrity of Workflow JSON Normalization
    #     @Scenario: Robust Error Handling and Exception Safety in Adverse Conditions

    #     Args:
    #         query (str): A non-empty string representing the user task query.
    #         top_k (int): Maximum number of similar workflows to retrieve.
    #         similarity_threshold (float): Minimum similarity score threshold.

    #     Returns:
    #         List[WorkflowTuple]: A list of tuples containing workflow id, description, workflow object, and similarity score.

    #     Raises:
    #         ValueError: If the query is invalid.
    #         WorkflowError: If embedding generation or database retrieval fails.
    #     """
    #     # Validate input
    #     if not isinstance(query, str) or not query.strip():
    #         raise ValueError("Query must be a non-empty string.")
        
    #     try:
    #         query_embedding = self.embedding_service.embed_texts(query)
    #         print(query_embedding)
    #         # query_embedding = self.embedding_service.model.encode(query).tolist()
    #         # Ensure we have a flat list
    #         if isinstance(query_embedding, list):
    #             # if isinstance(query_embedding[0], list):
    #             #     query_embedding = query_embedding[0]
    #             query_embedding = self.embedding_service.normalize_embedding(query_embedding)
                
    #             query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
    #     except Exception as e:
    #         logger.error("Error generating query embedding: %s", e)
    #         raise WorkflowError("Failed to generate query embedding") from e

    #     conn = None
    #     try:
    #         conn = psycopg2.connect(
    #             dbname=os.getenv("DB_NAME"),
    #             user=os.getenv("DB_USER"),
    #             password=os.getenv("DB_PASSWORD"),
    #             host=os.getenv("DB_HOST"),
    #             port=os.getenv("DB_PORT")
    #         )
    #         with conn.cursor() as cur:
    #             # Ensure the workflows table exists
    #             cur.execute("""
    #                 SELECT EXISTS (
    #                     SELECT FROM pg_tables 
    #                     WHERE schemaname = 'public' AND tablename = 'workflows'
    #                 );
    #             """)
    #             if not cur.fetchone()[0]:
    #                 logger.info("Table 'workflows' does not exist; returning empty result.")
    #                 return []

    #             sql_query = """
    #                 SELECT id, descriptions, workflow, 1 - (embedding <=> %s::vector) AS similarity
    #                 FROM workflows
    #                 WHERE 1 - (embedding <=> %s::vector) >= %s
    #                 ORDER BY similarity DESC
    #                 LIMIT %s;
    #             """
    #             cur.execute(sql_query, (query_embedding_str, query_embedding_str, similarity_threshold, top_k))
    #             results = cur.fetchall()

    #             # workflows: List[WorkflowTuple] = []
    #             # for row in results:
    #             #     wf_id, desc, wf_data, sim = row
    #             #     if isinstance(wf_data, str):
    #             #         wf_data = json.loads(wf_data)
    #             #     missing_nodes = wf_data.pop("missing_nodes", [])
    #             #     workflow_obj = Workflow(
    #             #         state=wf_data.get("state", {}),
    #             #         nodes=wf_data.get("nodes", []),
    #             #         edges=wf_data.get("edges", []),
    #             #         missing_nodes=missing_nodes
    #             #     )
    #             #     workflows.append((wf_id, desc, workflow_obj, sim))
    #             #     logger.info("Retrieved workflow id=%s with similarity=%.4f", wf_id, sim)
    #             # return workflows

    #             return [(id, desc, wf, sim) for id, desc, wf, sim in results if sim >= similarity_threshold]
    #     except Exception as e:
    #         logger.error("Error retrieving similar workflows: %s", e)
    #         raise WorkflowError("Database query failed") from e
    #     finally:
    #         if conn:
    #             conn.close()


            
    def save_workflow(
        self,
        *,
        descriptions: str,
        workflow_json: str,
        missing_nodes: List[Dict[str, Any]] = None,
        wf_id: str = None,
        name: str = None,
        tenant_id: str = None,
        user_id: str = None,
        group_id: str = None,
        is_public: bool = False,
        version: str = "1",
    ) -> str:
        """
        Save a workflow record in the database. Returns the workflow ID.
        If the tenant_id or user_id FK isn’t present, we log & continue.
        """
        # 1) Generate a new ID & name if needed
        wf_id = wf_id or str(uuid.uuid4())
        name  = name or f"Workflow_{wf_id}"

        # 2) Basic validation
        if not descriptions.strip():
            raise ValueError("Descriptions must be non-empty.")
        if not workflow_json.strip():
            raise ValueError("Workflow JSON must be non-empty.")

        # 3) Compute or normalize embedding
        try:
            emb_raw = self.embedding_service.embed_texts([descriptions])
            emb     = self.embedding_service.normalize_embedding(emb_raw)
            emb_str = "[" + ",".join(f"{x:.6f}" for x in emb[0]) + "]"
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            raise WorkflowError("Failed to generate embedding") from e

        # 4) Merge missing_nodes into JSON if provided
        data = json.loads(workflow_json)
        if missing_nodes:
            data["missing_nodes"] = missing_nodes
        wf_json_str = json.dumps(data)

        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO workflows (
                        id, name, tenant_id, user_id, group_id,
                        descriptions, workflow, embedding,
                        is_public, version
                    ) VALUES (
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,
                        %s,%s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name         = EXCLUDED.name,
                        tenant_id    = EXCLUDED.tenant_id,
                        user_id      = EXCLUDED.user_id,
                        group_id     = EXCLUDED.group_id,
                        descriptions = EXCLUDED.descriptions,
                        workflow     = EXCLUDED.workflow,
                        embedding    = EXCLUDED.embedding,
                        is_public    = EXCLUDED.is_public,
                        version      = EXCLUDED.version,
                        updated_at   = now();
                """, (
                    wf_id,
                    name,
                    tenant_id,
                    user_id,
                    group_id,
                    descriptions.strip(),
                    wf_json_str,
                    emb_str,
                    is_public,
                    version
                ))
                conn.commit()
                logger.info("Saved workflow %s", wf_id)

        except psycopg2.Error as e:
            # 23503 = foreign_key_violation
            if getattr(e, "pgcode", None) == errors.lookup("23503").pgcode:
                logger.warning("FK violation saving workflow (tenant/user missing); skipping persistence: %s", e)
            else:
                logger.error("Database insert failed: %s", e)
                raise WorkflowError("Failed to save workflow") from e

        finally:
            if conn:
                conn.close()

        return wf_id




