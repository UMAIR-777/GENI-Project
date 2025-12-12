



import os
from dotenv import load_dotenv
import numpy as np
from typing import List, Dict, Tuple
import psycopg2
import logging
import requests
from typing import List
from .connection import get_connection#

from sentence_transformers import SentenceTransformer
# no more huggingface_hub import

load_dotenv()

# Configure logging for production quality. Logging should integrate with centralized systems (e.g., ELK, Sentry)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generates and normalizes embeddings and handles batch storage for node embeddings,
    now using a local SentenceTransformer model only.
    """

    def __init__(self, model_path: str = None):
        # Determine local model path: either passed in or from ENV
        # self.model_path = model_path or os.getenv("LOCAL_MODEL_PATH")
        # self.model_path = "C:\\Users\\Home\\Desktop\\Keywords_Research\\New folder\\ai-workflow-research-py\\src\\ D\\downloaded\\sentence_transformers\\bge-m3\\BAAI_bge-m3\\models--BAAI--bge-m3\\snapshots\\5617a9f61b028005a4858fdac845db406aefb181"
        # if not self.model_path:
        #     raise ValueError("Must set LOCAL_MODEL_PATH environment variable or pass model_path")
        # Load the local model
        # self.model = SentenceTransformer(self.model_path)

        logger.info(f"Loaded local embedding model from")
        self.api_url = os.getenv("EMBEDDING_MODEL_URL")


    # def get_embeddings(self, text: str) -> List[float]:
    #     """
    #     Encode the given text using the local SentenceTransformer model.
    #     """
    #     return self.embed_texts(text, convert_to_numpy=True).tolist()
    



    def get_embeddings(self,text: str) -> list:
        """Generates embeddings for a given text using a locally loaded model."""
        # Encode the input text to generate embeddings
        embeddings = self.embed_texts([text])
        # Return the embeddings as a list
        return embeddings[0].tolist()
    

    


    def embed_texts(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        Send a list of strings to your embedding API and return the dense vectors.
        
        Args:
        texts: The input sentences to embed.
        api_url: Full URL of your /embed endpoint.

        Returns:
        A list of embedding vectors (one list of floats per input string).
        """
        payload = {"texts": texts}
        resp = requests.post(self.api_url, json=payload)
        resp.raise_for_status()              # will raise an error for non-2xx
        data = resp.json()
        return data["dense_vecs"]



    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """
        Normalize the provided embedding vector so that its Euclidean norm equals 1.
        """
        emb = np.array(embedding, dtype=float)
        if emb.size == 0:
            raise ValueError("Embedding is empty.")
        norm = np.linalg.norm(emb)
        if norm == 0:
            raise ValueError("Cannot normalize a zero vector.")
        return (emb / norm).tolist()
    
    def safe_join(self,field):
        if isinstance(field, list):
            return ', '.join(field)
        elif isinstance(field, str):
            return field
        else:
            return ''

    def generate_and_store_node_embeddings(self, nodes: List[Dict]) -> None:
        """
        Generate normalized embeddings for each node and store them in PostgreSQL.
        Ensures the node_embeddings table exists (with proper VECTOR dimension) before insertion.
        """
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("Input 'nodes' must be a non-empty list.")

        def format_embedding(emb: List[float]) -> str:
            return '[' + ','.join(f"{x:.6f}" for x in emb[0]) + ']'

        node_embeddings: List[Tuple] = []

        for node in nodes:
            try:
                node_id = node['id']

                for key in ('input', 'output', 'tags', 'description'):
                    value = node.get(key)
                    if not value or not isinstance(value, list):
                        raise ValueError(f"Node {node_id} missing or invalid '{key}' list.")

                # Special fix: handle cases where input fields are comma-separated strings inside list
                def process_text_fields(fields):
                    processed = []
                    for item in fields:
                        if isinstance(item, str):
                            split_items = [subitem.strip() for subitem in item.split(',')]
                            processed.extend(split_items)
                        else:
                            processed.append(str(item))
                    return ' '.join(processed)

                input_text = process_text_fields(node.get('input'))
                output_text = process_text_fields(node.get('output'))
                tags_text = process_text_fields(node.get('tags'))
                desc_text = process_text_fields(node.get('description'))

                # SPO must still be validated
                spo = node.get('spo', {})
                if not all(spo.get(k) for k in ('subject', 'predicate', 'object')):
                    raise ValueError(f"Node {node_id} has incomplete spo.")
                spo_text = f"{spo['subject']} {spo['predicate']} {spo['object']}"

                # Compute embeddings
                emb_in   = self.normalize_embedding(self.embed_texts([input_text]))
                emb_out  = self.normalize_embedding(self.embed_texts([output_text]))
                emb_tags = self.normalize_embedding(self.embed_texts([tags_text]))
                emb_desc = self.normalize_embedding(self.embed_texts([desc_text]))
                emb_spo  = self.normalize_embedding(self.embed_texts([spo_text]))
                overall_text = (
                    f"{node_id}: input: {input_text}; output: {output_text};"
                    f" tags: {tags_text}; description: {desc_text}; spo: {spo_text}"
                )
                emb_all  = self.normalize_embedding(self.embed_texts([overall_text]))

            except Exception as e:
                logger.error(f"Skipping node {node.get('id', '?')} due to error: {e}")
                continue

            node_embeddings.append((
                node_id,
                format_embedding(emb_in),
                format_embedding(emb_out),
                format_embedding(emb_tags),
                format_embedding(emb_desc),
                format_embedding(emb_spo),
                format_embedding(emb_all)
            ))
            logger.info(f"Prepared embeddings for node {node_id}")

        if not node_embeddings:
            logger.warning("No embeddings generated; nothing to insert.")
            return

        # Batch insert with table check/creation
        conn = get_connection()

        try:
            cur = conn.cursor()
            # Ensure 'vector' extension and table exists
            # dim = self.model.get_sentence_embedding_dimension()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS nodes_embeddings (
                    node_id TEXT PRIMARY KEY,
                    input_embedding  VECTOR(1024),
                    output_embedding VECTOR(1024),
                    tags_embedding   VECTOR(1024),
                    description_embedding VECTOR(1024),
                    spo_embedding    VECTOR(1024),
                    overall_embedding VECTOR(1024)
                );
            """)

            args_str = ','.join(
                cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)", tpl).decode()
                for tpl in node_embeddings
            )
            insert_sql = (
                "INSERT INTO nodes_embeddings "
                "(node_id, input_embedding, output_embedding, tags_embedding, "
                "description_embedding, spo_embedding, overall_embedding) VALUES "
                f"{args_str} "
                "ON CONFLICT (node_id) DO UPDATE SET "
                "input_embedding = EXCLUDED.input_embedding, "
                "output_embedding = EXCLUDED.output_embedding, "
                "tags_embedding = EXCLUDED.tags_embedding, "
                "description_embedding = EXCLUDED.description_embedding, "
                "spo_embedding = EXCLUDED.spo_embedding, "
                "overall_embedding = EXCLUDED.overall_embedding;"
            )
            cur.execute(insert_sql)
            conn.commit()
            logger.info("Node embeddings stored successfully.")
        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    # def generate_and_store_node_embeddings(self, nodes: List[Dict]) -> int:
    #     """
    #     Generate normalized embeddings for each node and store them in PostgreSQL.
    #     Returns the number of rows inserted/updated.
    #     Raises if no embeddings could be prepared, or on any DB error.
    #     """
    #     print(f"[EMBED DEBUG] 1) Starting embedding generation for {len(nodes)} node(s)")
    #     if not isinstance(nodes, list) or not nodes:
    #         raise ValueError("Input 'nodes' must be a non-empty list.")

    #     # Will hold tuples of (node_id, emb_in, emb_out, emb_tags, emb_desc, emb_spo, emb_all)
    #     prepared: List[Tuple[str,str,str,str,str,str,str]] = []

    #     # --- 2) Prepare embeddings for each node
    #     for node in nodes:
    #         node_id = node.get("id")
    #         print(f"[EMBED DEBUG] 2) Processing node {node_id}")
    #         try:
    #             # a) Validate fields are lists
    #             for key in ("input","output","tags","description"):
    #                 val = node.get(key)
    #                 if not isinstance(val, list) or not val:
    #                     raise ValueError(f"Node {node_id} invalid or missing list '{key}'")

    #             # b) Flatten lists into strings
    #             def flatten(lst: List[str]) -> str:
    #                 parts = []
    #                 for item in lst:
    #                     if isinstance(item, str):
    #                         parts.extend(s.strip() for s in item.split(","))
    #                     else:
    #                         parts.append(str(item))
    #                 return " ".join(parts)

    #             in_txt   = flatten(node["input"])
    #             out_txt  = flatten(node["output"])
    #             tags_txt = flatten(node["tags"])
    #             desc_txt = flatten(node["description"])
    #             print(f"[EMBED DEBUG]    input_text:   {in_txt!r}")
    #             print(f"[EMBED DEBUG]    output_text:  {out_txt!r}")
    #             print(f"[EMBED DEBUG]    tags_text:    {tags_txt!r}")
    #             print(f"[EMBED DEBUG]    desc_text:    {desc_txt!r}")

    #             # c) Validate SPO
    #             spo = node.get("spo", {})
    #             if not all(spo.get(k) for k in ("subject","predicate","object")):
    #                 raise ValueError(f"Node {node_id} has incomplete spo")
    #             spo_txt = f"{spo['subject']} {spo['predicate']} {spo['object']}"
    #             print(f"[EMBED DEBUG]    spo_text:     {spo_txt!r}")

    #             # d) Generate embeddings
    #             # Each embed_texts returns a list of vectors; we take [0]
    #             emb = lambda text: self.normalize_embedding(self.embed_texts([text]))[0]
    #             emb_in   = emb(in_txt)
    #             emb_out  = emb(out_txt)
    #             emb_tags = emb(tags_txt)
    #             emb_desc = emb(desc_txt)
    #             emb_spo  = emb(spo_txt)

    #             all_txt = f"{node_id}: {in_txt}; {out_txt}; {tags_txt}; {desc_txt}; {spo_txt}"
    #             emb_all  = emb(all_txt)

    #             print(f"[EMBED DEBUG]    raw embeddings lengths: "
    #                   f"{len(emb_in)},{len(emb_out)},{len(emb_tags)},{len(emb_desc)},{len(emb_spo)},{len(emb_all)}")

    #         except Exception as e:
    #             print(f"[EMBED DEBUG]  ❌ Skipping node {node_id}: {e}")
    #             raise  # if you want to abort everything, or use `continue` to skip only this node

    #         # e) Format as Postgres vector literal
    #         def to_vec(v: List[float]) -> str:
    #             return "[" + ",".join(f"{x:.6f}" for x in v) + "]"

    #         prepared.append((
    #             node_id,
    #             to_vec(emb_in),
    #             to_vec(emb_out),
    #             to_vec(emb_tags),
    #             to_vec(emb_desc),
    #             to_vec(emb_spo),
    #             to_vec(emb_all),
    #         ))
    #         print(f"[EMBED DEBUG]  ✅ Prepared embeddings tuple for {node_id}")

    #     # --- 3) Ensure we actually have something to insert
    #     if not prepared:
    #         print("[EMBED DEBUG]  ❌ No embeddings were prepared; aborting storage")
    #         raise RuntimeError("No embeddings generated; aborting storage")

    #     # --- 4) Insert into Postgres
    #     print(f"[EMBED DEBUG] 4) Connecting to DB, inserting {len(prepared)} row(s)")
    #     conn = get_connection()
    #     try:
    #         cur = conn.cursor()
    #         # a) Ensure extension & table
    #         print("[EMBED DEBUG]    Ensuring vector extension + table exist")
    #         cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    #         cur.execute("""
    #             CREATE TABLE IF NOT EXISTS nodes_embeddings (
    #               node_id               TEXT PRIMARY KEY,
    #               input_embedding       VECTOR(1024),
    #               output_embedding      VECTOR(1024),
    #               tags_embedding        VECTOR(1024),
    #               description_embedding VECTOR(1024),
    #               spo_embedding         VECTOR(1024),
    #               overall_embedding     VECTOR(1024)
    #             );
    #         """)

    #         # b) Bulk upsert
    #         sql = """
    #           INSERT INTO nodes_embeddings (
    #             node_id,
    #             input_embedding, output_embedding,
    #             tags_embedding, description_embedding,
    #             spo_embedding, overall_embedding
    #           )
    #           VALUES %s
    #           ON CONFLICT (node_id) DO UPDATE SET
    #             input_embedding       = EXCLUDED.input_embedding,
    #             output_embedding      = EXCLUDED.output_embedding,
    #             tags_embedding        = EXCLUDED.tags_embedding,
    #             description_embedding = EXCLUDED.description_embedding,
    #             spo_embedding         = EXCLUDED.spo_embedding,
    #             overall_embedding     = EXCLUDED.overall_embedding;
    #         """
    #         print(f"[EMBED DEBUG]    Executing upsert")
    #         execute_values(cur, sql, prepared, template=None, page_size=100)
    #         conn.commit()
    #         print(f"[EMBED DEBUG]  ✅ Embeddings stored: {len(prepared)} row(s)")
    #         return len(prepared)


    #     except Exception as e:
    #         conn.rollback()
    #         print(f"[EMBED DEBUG]  ❌ Failed to store embeddings: {e}")
    #         raise
    #     finally:
    #         cur.close()
    #         conn.close()
