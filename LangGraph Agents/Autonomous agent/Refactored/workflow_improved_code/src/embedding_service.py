# import os
# from dotenv import load_dotenv
# import numpy as np
# import shutil
# import re
# import numpy as np
# from typing import List, Union
# from sentence_transformers import SentenceTransformer
# from typing import List, Union, Optional, Dict, Tuple
# from huggingface_hub import InferenceClient
# import psycopg2
# import logging
# load_dotenv()

# # Configure logging for production quality. Logging should integrate with centralized systems (e.g., ELK, Sentry)
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
# logger = logging.getLogger(__name__)

# class EmbeddingService:
#     """
#     Generates and normalizes embeddings and handles batch storage for node embeddings.
#     """

#     # def __init__(self, client: InferenceClient = None):
#     #     if client is None:
#     #         raise ValueError("InferenceClient is required for embedding generation")
#     #     self.client = client

#     def __init__(self, client: InferenceClient = None):
#         self.client = client
#         if self.client is None:
#             # Load the local model
#             model_name = os.getenv("EMBEDDING_MODEL")
#             if model_name is None:
#                 raise ValueError("EMBEDDING_MODEL must be set in the .env file.")

#             # Standardize the model name
#             standardized_model_name = self.standardize_model_name(model_name)

#             # Construct the model path
#             base_model_path = os.getenv("LOCAL_MODEL_PATH")
#             model_path = os.path.join(base_model_path, standardized_model_name)

#             # Check if the model exists, if not download it
#             if not os.path.exists(model_path):
#                 logger.info(f"Model not found at {model_path}. Downloading...")
#                 try:
#                     # Create the temporary directory inside sentence_transformers
#                     temp_dir = os.path.join(base_model_path, "temp")
#                     os.makedirs(temp_dir, exist_ok=True)

#                     # Get the Hugging Face API token
#                     hf_api_token = os.getenv("HF_API_TOKEN")
#                     if not hf_api_token:
#                         raise ValueError("HF_API_TOKEN must be set in the .env file for private or gated models.")

#                     # Download the model to the temporary directory
#                     temp_model = SentenceTransformer(model_name, cache_folder=temp_dir, use_auth_token=hf_api_token)
#                     temp_model.save(temp_dir)

#                     # Move the model files to the standardized directory
#                     for item in os.listdir(temp_dir):
#                         s = os.path.join(temp_dir, item)
#                         d = os.path.join(model_path, item)
#                         try:
#                             if os.path.isdir(s):
#                                 shutil.copytree(s, d)  # Use copytree for directories
#                             else:
#                                 shutil.copy2(s, d)  # Use copy2 to preserve metadata
#                         except OSError as e:
#                             logger.error(f"Error moving file {s} to {d}: {e}")
#                             raise

#                     # Remove the temporary directory
#                     shutil.rmtree(temp_dir)
#                     logger.info(f"Model downloaded and saved to {model_path}")
#                 except Exception as e:
#                     logger.error(f"Error downloading or saving local model: {e}")
#                     raise
#             try:
#                 self.model = SentenceTransformer(model_path)
#                 logger.info(f"Local model loaded from {model_path}")
#             except Exception as e:
#                 logger.error(f"Error loading local model: {e}")
#                 raise
#         else:
#             self.model = None
#             logger.info("InferenceClient is provided, skipping local model loading.")

#     def get_embeddings(self, text: str) -> List[float]:
#         """
#         Generate an embedding vector for the provided text using a preloaded SentenceTransformer model.
        
#         @Feature: Embedding Generation and Normalization
#         @Scenario: Generate normalized embedding vector for valid text input
#         @Scenario: Handle multi-dimensional arrays and batch outputs consistently
#         @Scenario: Validate input integrity and handle edge cases robustly
        
#         Args:
#             text (str): A non-empty string to be converted into an embedding vector.
            
#         Returns:
#             List[float]: A flattened list of floats representing the embedding vector.
            
#         Raises:
#             ValueError: If the input text is not a string or is empty/whitespace.
#             RuntimeError: If embedding generation fails or returns unexpected format.
#         """
#         if not isinstance(text, str):
#             raise ValueError("Input text must be a string.")
#         if not text.strip():
#             raise ValueError("Input text must not be empty or whitespace.")
        
#         try:
#             # Key changes:
#             # 1. Use convert_to_tensor=False to get numpy array directly
#             # 2. Use batch_size=1 for consistent output format
#             embeddings = self.model.encode(text, convert_to_tensor=False, batch_size=1)
            
#             if embeddings is None or (isinstance(embeddings, np.ndarray) and embeddings.size == 0):
#                 raise RuntimeError("Embedding generation returned an empty result.")
                
#             # Handle both single vector and batch outputs
#             if isinstance(embeddings, np.ndarray):
#                 if embeddings.ndim > 1:
#                     embeddings = embeddings.flatten()
#                 return embeddings.tolist()
#             elif isinstance(embeddings, list):
#                 return embeddings
#             else:
#                 raise RuntimeError("Unexpected type returned from embedding generation.")
#         except Exception as e:
#             raise RuntimeError(f"Failed to generate embedding for text: {e}") from e

#     def normalize_embedding(self, embedding: Union[List[float], np.ndarray]) -> List[float]:
#         """
#         Normalize the provided embedding vector so that its Euclidean norm equals 1. This function
#         accepts both list and numpy array representations of the embedding.
        
#         @Feature: Embedding Generation and Normalization
#         @Scenario: Normalize a valid embedding vector; raise error on zero-norm vector
        
#         Args:
#             embedding (Union[List[float], np.ndarray]): The embedding vector to normalize.
            
#         Returns:
#             List[float]: A normalized embedding vector as a list of floats.
            
#         Raises:
#             ValueError: If the embedding is not a list or numpy array, is empty, or has zero norm.
#         """
#         if isinstance(embedding, list):
#             embedding = np.array(embedding)
#         if not isinstance(embedding, np.ndarray):
#             raise ValueError("Embedding must be provided as a list or numpy array.")
#         if embedding.size == 0:
#             raise ValueError("Embedding is empty.")
        
#         norm = np.linalg.norm(embedding)
#         if norm == 0:
#             raise ValueError("Embedding norm is zero; cannot normalize a zero vector.")
        
#         normalized = embedding / norm
#         return normalized.tolist()

#     def standardize_model_name(self, model_name: str) -> str:
#         """
#         Standardizes a model name to create a valid and consistent directory name.
#         """
#         # Replace any non-alphanumeric characters with underscores
#         standardized_name = re.sub(r'[^a-zA-Z0-9]+', '_', model_name)
#         # Remove leading and trailing underscores
#         standardized_name = standardized_name.strip('_')
#         # Convert to lowercase
#         standardized_name = standardized_name.lower()
#         return standardized_name
        
#     # def get_embeddings(self, text: str) -> list:
#     #     """Generates embeddings for a given text using Hugging Face API."""
#     #     response = self.client.feature_extraction(text, model="sentence-transformers/all-MiniLM-L6-v2")
#     #     return response.tolist()

#     def generate_and_store_node_embeddings(self, nodes: List[Dict]) -> None:
#         """
#         Generate normalized embeddings for each node in the provided list and store them in the PostgreSQL
#         table 'node_embeddings'. Each node must be a dictionary containing:
#         - 'id': Unique identifier.
#         - 'input': List of input strings.
#         - 'output': List of output strings.
#         - 'tags': List of tag strings.
#         - 'description': List of description strings.
#         - 'SPO': A dictionary with keys 'subject', 'predicate', 'object'.
        
#         The function validates each node's data, generates embeddings for each textual component, normalizes 
#         the embeddings, and then performs a batch insertion using secure SQL operations. Robust error handling 
#         ensures that any node with faulty data is skipped, and database connectivity issues are explicitly handled.
        
#         @Feature: Generate & Store Node Embeddings
#         @Scenario: Process nodes to generate and normalize embeddings and persist them reliably
#         @Scenario: Robustly handle errors from missing data, invalid inputs, and database connectivity issues
        
#         Args:
#             nodes (List[Dict]): A non-empty list of node dictionaries.
        
#         Raises:
#             ValueError: If 'nodes' is not a non-empty list.
#             RuntimeError: If database connectivity or insertion fails critically.
#         """
#         if not isinstance(nodes, list) or len(nodes) == 0:
#             raise ValueError("Input 'nodes' must be a non-empty list of node dictionaries.")
        
#         def format_embedding(emb: List[float]) -> str:
#             # Format the embedding vector as a string with 6 decimal precision, e.g., "[0.123456,0.654321,...]"
#             return '[' + ','.join(f"{x:.6f}" for x in emb) + ']'
        
#         node_embeddings: List[Tuple] = []
        
#         for node in nodes:
#             try:
#                 node_id = node.get('id')
#                 if not node_id:
#                     raise ValueError("Node is missing the required 'id' key.")
                
#                 # Extract and validate textual components
#                 input_list = node.get('input')
#                 output_list = node.get('output')
#                 tags_list = node.get('tags')
#                 description_list = node.get('description')
#                 spo = node.get('SPO', {})
                
#                 if not isinstance(input_list, list) or not input_list:
#                     raise ValueError(f"Node '{node_id}' must have a non-empty 'input' list.")
#                 if not isinstance(output_list, list) or not output_list:
#                     raise ValueError(f"Node '{node_id}' must have a non-empty 'output' list.")
#                 if not isinstance(tags_list, list) or not tags_list:
#                     raise ValueError(f"Node '{node_id}' must have a non-empty 'tags' list.")
#                 if not isinstance(description_list, list) or not description_list:
#                     raise ValueError(f"Node '{node_id}' must have a non-empty 'description' list.")
#                 if not isinstance(spo, dict) or not spo.get('subject') or not spo.get('predicate') or not spo.get('object'):
#                     raise ValueError(f"Node '{node_id}' must have complete 'SPO' information.")
                
#                 input_text = ', '.join(input_list)
#                 output_text = ', '.join(output_list)
#                 tags_text = ', '.join(tags_list)
#                 description_text = ', '.join(description_list)
#                 spo_text = f"{spo.get('subject')} {spo.get('predicate')} {spo.get('object')}".strip()
#                 print(f"\nNode ID: {node_id}, SPO (spo_text): {spo_text}n")
                
#                 # Generate and normalize embeddings for each component
#                 input_embedding = self.normalize_embedding(self.get_embeddings(input_text))
#                 output_embedding = self.normalize_embedding(self.get_embeddings(output_text))
#                 tags_embedding = self.normalize_embedding(self.get_embeddings(tags_text))
#                 description_embedding = self.normalize_embedding(self.get_embeddings(description_text))
#                 spo_embedding = self.normalize_embedding(self.get_embeddings(spo_text))
#                 overall_text = f"{node_id}: input: {input_text}; output: {output_text}; tags: {tags_text}; description: {description_text}; SPO: {spo_text}"
#                 overall_embedding = self.normalize_embedding(self.get_embeddings(overall_text))
#             except Exception as e:
#                 logger.error(f"Error generating embeddings for node '{node.get('id', 'unknown')}': {e}")
#                 continue  # Skip faulty node
            
#             logger.info(f"Generated embeddings for node: {node_id}")
#             logger.debug(f"Input text: {input_text}")
#             logger.debug(f"Output text: {output_text}")
#             logger.debug(f"Tags text: {tags_text}")
#             logger.debug(f"Description text: {description_text}")
#             logger.debug(f"SPO text: {spo_text}")
            
#             # Append formatted embeddings as a tuple
#             node_embeddings.append((
#                 node_id,
#                 format_embedding(input_embedding),
#                 format_embedding(output_embedding),
#                 format_embedding(tags_embedding),
#                 format_embedding(description_embedding),
#                 format_embedding(spo_embedding),
#                 format_embedding(overall_embedding)
#             ))
        
#         if not node_embeddings:
#             logger.warning("No valid node embeddings generated; aborting database insertion.")
#             return
        
#         # Perform batch insertion into the database with robust error handling.
#         try:
#             conn = psycopg2.connect(
#                 dbname=os.getenv("DB_NAME"),
#                 user=os.getenv("DB_USER"),
#                 password=os.getenv("DB_PASSWORD"),
#                 host=os.getenv("DB_HOST"),
#                 port=os.getenv("DB_PORT")
#             )
#             cur = conn.cursor()
#         except Exception as e:
#             logger.error(f"Database connection error: {e}")
#             raise RuntimeError("Failed to establish a database connection.") from e
        
#         try:
#             # Use mogrify to safely format batch insert arguments.
#             args_str = ','.join(
#                 cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)", item).decode('utf-8')
#                 for item in node_embeddings
#             )
#             insert_query = (
#                 "INSERT INTO node_embeddings (node_id, input_embedding, output_embedding, "
#                 "tags_embedding, description_embedding, spo_embedding, overall_embedding) VALUES " +
#                 args_str +
#                 " ON CONFLICT (node_id) DO UPDATE SET "
#                 "input_embedding = EXCLUDED.input_embedding, "
#                 "output_embedding = EXCLUDED.output_embedding, "
#                 "tags_embedding = EXCLUDED.tags_embedding, "
#                 "description_embedding = EXCLUDED.description_embedding, "
#                 "spo_embedding = EXCLUDED.spo_embedding, "
#                 "overall_embedding = EXCLUDED.overall_embedding;"
#             )
#             cur.execute(insert_query)
#             conn.commit()
#             logger.info("Successfully stored node embeddings in the database.")
#         except psycopg2.Error as e:
#             if e.pgcode == '42P01':
#                 logger.info("Table 'node_embeddings' does not exist; skipping node embedding storage.")
#             else:
#                 logger.error(f"Database insertion error: {e}")
#                 raise RuntimeError("Failed to insert node embeddings into the database.") from e
#         finally:
#             cur.close()
#             conn.close()



# embedding_service.py
"""
High-performance EmbeddingService module with clear separation of concerns:
- ConfigLoader: loads & validates environment
- ModelManager: downloads & loads SentenceTransformer or uses InferenceClient
- EmbeddingService: exposes get_embeddings, normalize_embedding, generate_and_store_node_embeddings
- DBClient: batch upsert into PostgreSQL

Follows Google engineering best practices, SOLID, robust input validation,
comprehensive error handling, and BDD-aligned docstrings.
"""
import os
import shutil
import re
import logging
from typing import TypedDict, List, Dict, Union, Optional, Tuple, Callable
import numpy as np
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
import psycopg2
from psycopg2 import OperationalError, Error

# Constants
DB_TABLE_NAME = "node_embeddings"
MAX_EMBEDDING_DIM = 1024
TEMP_DOWNLOAD_DIR = "temp_download"

# Typed definitions
class NodeDict(TypedDict):
    id: str
    input: List[str]
    output: List[str]
    tags: List[str]
    description: List[str]
    SPO: Dict[str, str]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

class ConfigLoader:
    """Loads and validates environment configuration."""

    @staticmethod
    def load_env_var(name: str, required: bool = True) -> str:
        value = os.getenv(name)
        if required and not value:
            logger.error(f"{name} must be set in environment.")
            raise ValueError(f"{name} must be set in environment.")
        return value or ""

class ModelManager:
    """Handles download, caching, and loading of embedding models."""

    def __init__(self,
                 model_name: str,
                 cache_dir: str,
                 hf_token: Optional[str] = None,
                 infer_client: Optional[InferenceClient] = None):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.hf_token = hf_token
        self.infer_client = infer_client
        self.local_model: Optional[SentenceTransformer] = None
        self._ensure_model()

    def _standardize_name(self) -> str:
        name = re.sub(r'[^a-zA-Z0-9]+', '_', self.model_name)
        return name.strip('_').lower()

    def _ensure_model(self) -> None:
        if self.infer_client:
            logger.info("InferenceClient provided; skipping local model handling.")
            return

        std_name = self._standardize_name()
        model_dir = os.path.join(self.cache_dir, std_name)
        if not os.path.isdir(model_dir):
            # Commenting out download model as model is already downloaded
            # self._download_model(model_dir)
            logger.info(f"Model directory {model_dir} does not exist, but skipping download as per configuration.")
        self._load_local_model(model_dir)
        
    # Not Passed Test
    # def _download_model(self, dest: str) -> None: 
    #     token = self.hf_token or ConfigLoader.load_env_var('HF_API_TOKEN') 
    #     os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True) 
    #     try: 
    #         temp = SentenceTransformer(self.model_name,
    #                                    cache_folder=TEMP_DOWNLOAD_DIR,
    #                                    use_auth_token=token)
    #         temp.save(TEMP_DOWNLOAD_DIR)
    #         # shutil.move(TEMP_DOWNLOAD_DIR, dest)
    #         shutil.copytree(TEMP_DOWNLOAD_DIR, dest) 
    #         logger.info(f"Model downloaded to {dest}") 
    #     except Exception as e: 
    #         logger.error(f"Error downloading or saving local model: {e}") 
    #         raise RuntimeError(f"Failed to download model: {e}") 
    #     finally: 
    #         if os.path.isdir(TEMP_DOWNLOAD_DIR): 
    #             shutil.rmtree(TEMP_DOWNLOAD_DIR) 

    def _load_local_model(self, path: str) -> None:
        try:
            self.local_model = SentenceTransformer(path)
            logger.info(f"Loaded model from {path}")
        except Exception as e:
            logger.error(f"Load error: {e}")
            raise RuntimeError(f"Failed to load model: {e}")

    def encode(self, text: str) -> Union[np.ndarray, List[float]]:
        if self.infer_client:
            resp = self.infer_client.embeddings(texts=[text])  # type: ignore
            return resp[0]['embedding']
        assert self.local_model is not None
        return self.local_model.encode(text, convert_to_tensor=False, batch_size=1)  # type: ignore

class DBClient:
    """Manages database connections and batch upserts."""
    def __init__(self, connect_fn: Callable = psycopg2.connect):
        self.connect_fn = connect_fn

    def upsert_embeddings(self, rows: List[Tuple]) -> None:
        conn = None
        try:
            conn = self.connect_fn(
                dbname=ConfigLoader.load_env_var('DB_NAME'),
                user=ConfigLoader.load_env_var('DB_USER'),
                password=ConfigLoader.load_env_var('DB_PASSWORD'),
                host=ConfigLoader.load_env_var('DB_HOST'),
                port=ConfigLoader.load_env_var('DB_PORT')
            )
            with conn, conn.cursor() as cur:
                args = ','.join(
                    cur.mogrify("(%s,%s,%s,%s,%s,%s,%s)", r).decode()
                    for r in rows
                )
                sql = (
                    f"INSERT INTO {DB_TABLE_NAME}"
                    "(node_id,input_embedding,output_embedding,tags_embedding,description_embedding,spo_embedding,overall_embedding)"
                    f" VALUES {args}"
                    " ON CONFLICT (node_id) DO UPDATE SET"
                    " input_embedding=EXCLUDED.input_embedding,"  
                    " output_embedding=EXCLUDED.output_embedding,"  
                    " tags_embedding=EXCLUDED.tags_embedding,"  
                    " description_embedding=EXCLUDED.description_embedding,"  
                    " spo_embedding=EXCLUDED.spo_embedding,"  
                    " overall_embedding=EXCLUDED.overall_embedding;"
                )
                cur.execute(sql)
                logger.info("Upsert successful")
        except OperationalError as oe:
            logger.error(f"DB connection failed: {oe}")
            raise RuntimeError("DB connection error")
        except Error as db_err:
            if getattr(db_err, 'pgcode', None) == '42P01':
                logger.info("Table missing; skipping upsert.")
            else:
                logger.error(f"DB error: {db_err}")
                raise RuntimeError(f"DB upsert error: {db_err}")
        finally:
            if conn:
                conn.close()

class EmbeddingService:
    """
    Service orchestrating embedding generation, normalization, and storage.
    """
    def __init__(
        self,
        client: Optional[InferenceClient] = None,
        db_client: Optional[DBClient] = None
    ):
        # Load config
        model_name = ConfigLoader.load_env_var('EMBEDDING_MODEL')
        cache_dir = ConfigLoader.load_env_var('LOCAL_MODEL_PATH')
        token = os.getenv('HF_API_TOKEN', None)
        # Init dependencies
        self.model_mgr = ModelManager(model_name, cache_dir, hf_token=token, infer_client=client)
        self.db_client = db_client or DBClient()

    def get_embeddings(self, text: str) -> List[float]:
        """Returns embedding vector for text after validations."""
        if not isinstance(text, str):
            raise ValueError("Input text must be a string.")
        if not text.strip():
            raise ValueError("Input text must not be empty or whitespace.")
        try:
            emb = self.model_mgr.encode(text)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}. Retrying once.")
            try:
                emb = self.model_mgr.encode(text)
            except Exception as e2:
                logger.error(f"Retry failed: {e2}")
                raise RuntimeError(f"Failed to generate embedding after retry: {e2}") from e2
        vec = np.asarray(emb).astype(float)
        if vec.size == 0:
            raise RuntimeError("Empty embedding returned.")
        if vec.ndim > 1:
            vec = vec.flatten()
        if vec.size > MAX_EMBEDDING_DIM:
            logger.warning("Embedding exceeds max dim; truncating.")
            vec = vec[:MAX_EMBEDDING_DIM]
        return vec.tolist()

    def normalize_embedding(self, embedding: Union[List[float], np.ndarray]) -> List[float]:
        """Normalizes vector to unit length with validations."""
        arr = np.asarray(embedding, dtype=float)
        if arr.size == 0:
            raise ValueError("Embedding is empty.")
        norm = np.linalg.norm(arr)
        if norm == 0:
            raise ValueError("Cannot normalize zero vector.")
        return (arr / norm).tolist()

    def generate_and_store_node_embeddings(self, nodes: List[NodeDict]) -> None:
        """Generates, normalizes, and upserts embeddings for a list of nodes."""
        if not nodes:
            raise ValueError("Input 'nodes' must be a non-empty list.")
        rows: List[Tuple] = []
        for node in nodes:
            nid = node.get('id')
            if not nid:
                logger.error("Node missing 'id'; skipping.")
                continue
            try:
                for key in ('input','output','tags','description'):
                    vals = node.get(key)
                    if not isinstance(vals, list) or not vals:
                        raise ValueError(f"'{key}' list invalid for node {nid}.")
                spo = node.get('SPO', {})
                if not all(spo.get(k) for k in ('subject','predicate','object')):
                    raise ValueError(f"Incomplete SPO for node {nid}.")
                texts = [", ".join(node[k]) for k in ('input','output','tags','description')]
                spo_txt = f"{spo['subject']} {spo['predicate']} {spo['object']}"
                all_txt = f"{nid}|" + "|".join(texts) + f"|{spo_txt}"
                embeds = [
                    self.normalize_embedding(self.get_embeddings(t)) for t in texts + [spo_txt, all_txt]
                ]
                def fmt(v: List[float]) -> str:
                    return '[' + ','.join(f"{x:.6f}" for x in v) + ']'
                rows.append((nid, *(fmt(e) for e in embeds)))
            except Exception as e:
                logger.error(f"Node {nid} error: {e}")
        if not rows:
            logger.warning("No embeddings to upsert.")
            return
        self.db_client.upsert_embeddings(rows)

########## -------------------- New embedding service using external API ----------------------- #######################

# import os
# import requests
# from typing import List

# class EmbeddingService:
#     """
#     Embedding service that uses external API to get embeddings.
#     """
#     def __init__(self, api_url: str = None, db_client: Optional[DBClient] = None):
        
#         self.db_client = db_client or DBClient()
#         # self.api_url = api_url or os.getenv("EMBEDDING_API_URL") or "https://bge-m3-v1-998052755917.us-central1.run.app/embed"
#         self.api_url =  os.getenv("EMBEDDING_API_URL")
#         if not self.api_url:
#             raise ValueError("Embedding API URL is required.")
#         if self.api_url:
#             print(f"\n---------- Using external API for embeddings --------- \n")

#     def get_embeddings(self, text: str) -> List[float]:
#         if not isinstance(text, str) or not text.strip():
#             raise ValueError("Input text must be a non-empty string.")
#         payload = {"texts": [text]}
#         response = requests.post(self.api_url, json=payload)
#         response.raise_for_status()
#         data = response.json()
#         dense_vecs = data.get("dense_vecs")
#         if not dense_vecs or not isinstance(dense_vecs, list) or not dense_vecs[0]:
#             raise RuntimeError("Invalid response from embedding API.")
#         return dense_vecs[0]

#     def normalize_embedding(self, embedding: List[float]) -> List[float]:
#         import numpy as np
#         arr = np.array(embedding, dtype=float)
#         norm = np.linalg.norm(arr)
#         if norm == 0:
#             raise ValueError("Cannot normalize zero vector.")
#         return (arr / norm).tolist()

#     # def generate_and_store_node_embeddings(self, nodes: List[dict]) -> None:
#     #     # This method can be implemented similarly by calling get_embeddings for each node's text fields
#     #     # and then storing them in the database as before.
#     #     raise NotImplementedError("Batch embedding and storage not implemented for API client yet.")

#     def generate_and_store_node_embeddings(self, nodes: List[NodeDict]) -> None:
#         """Generates, normalizes, and upserts embeddings for a list of nodes."""
#         if not nodes:
#             raise ValueError("Input 'nodes' must be a non-empty list.")
#         rows: List[Tuple] = []
#         for node in nodes:
#             nid = node.get('id')
#             if not nid:
#                 logger.error("Node missing 'id'; skipping.")
#                 continue
#             try:
#                 for key in ('input','output','tags','description'):
#                     vals = node.get(key)
#                     if not isinstance(vals, list) or not vals:
#                         raise ValueError(f"'{key}' list invalid for node {nid}.")
#                 spo = node.get('SPO', {})
#                 if not all(spo.get(k) for k in ('subject','predicate','object')):
#                     raise ValueError(f"Incomplete SPO for node {nid}.")
#                 texts = [", ".join(node[k]) for k in ('input','output','tags','description')]
#                 spo_txt = f"{spo['subject']} {spo['predicate']} {spo['object']}"
#                 all_txt = f"{nid}|" + "|".join(texts) + f"|{spo_txt}"
#                 embeds = [
#                     self.normalize_embedding(self.get_embeddings(t)) for t in texts + [spo_txt, all_txt]
#                 ]
#                 def fmt(v: List[float]) -> str:
#                     return '[' + ','.join(f"{x:.6f}" for x in v) + ']'
#                 rows.append((nid, *(fmt(e) for e in embeds)))
#             except Exception as e:
#                 logger.error(f"Node {nid} error: {e}")
#         if not rows:
#             logger.warning("No embeddings to upsert.")
#             return
#         self.db_client.upsert_embeddings(rows)
