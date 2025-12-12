from typing import TypedDict, List, Dict, Tuple, Literal, Optional, Any
import json
import numpy as np
from langgraph.graph import StateGraph, END, START
from langchain_groq import ChatGroq
from jsonschema import validate, ValidationError
from huggingface_hub import InferenceClient
import psycopg2
from dotenv import load_dotenv
import os
import re
import logging
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from psycopg2.extensions import adapt, register_adapter, AsIs
from psycopg2.pool import ThreadedConnectionPool
from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES


# Load environment variables from .env file
load_dotenv()

# Define your desired directory
# Define the local path where the model was stored

local_model_path = os.getenv("LOCAL_MODEL_PATH")
model_used = os.getenv("MODEL_USED")
model = SentenceTransformer(local_model_path)
llm = ChatGroq(temperature=0, model=model_used)

# Node schema definition

NODE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "input": {"type": "array", "items": {"type": "string"}},
            "output": {"type": "array", "items": {"type": "string"}},
            "tags": {"type": "array", "items": {"type": "string"}},
            "description": {"type": "array", "items": {"type": "string"}},
            "SPO": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "object": {"type": "string"}
                },
                "required": ["subject", "predicate", "object"]
            }
        },
        "required": ["id", "input", "output", "tags", "description", "SPO"]
    }
}

# Enable numpy array adaptation for PostgreSQL
def adapt_numpy_array(numpy_array):
    return AsIs("'" + str(list(numpy_array)) + "'")
register_adapter(np.ndarray, adapt_numpy_array)

# ========================================
# Production-Grade Database Setup Function
# ========================================

file_path = os.getenv("SQL_File_Path")

def load_sql_file(file_path: str) -> str:
    with open(file_path, 'r') as f:
        return f.read()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enable numpy array adaptation
def adapt_numpy_array(numpy_array):
    return psycopg2.extensions.AsIs("'" + str(list(numpy_array)) + "'")
register_adapter(np.ndarray, adapt_numpy_array)

# Connection pool
pool = ThreadedConnectionPool(
    minconn=1, maxconn=20,
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)

def setup_database(sql_file_path: str = file_path) -> None:
    """
    Setup the PostgreSQL database with vector support and indexes.
    @Feature High-Performance Workflow Node Matching
    @Scenario Setup Database with Vector Support and Indexes
    """
    conn = pool.getconn()
    cur = conn.cursor()
    try:
        sql_commands = load_sql_file(sql_file_path)
        cur.execute(sql_commands)
        conn.commit()
        logger.info("Database setup completed successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Database setup failed: {str(e)}")
        raise
    finally:
        cur.close()
        pool.putconn(conn)

# Call setup
setup_database()

# Retrieve similar workflows from database
def retrieve_similar_workflow(query: str, top_k: int = 1, similarity_threshold: float = 0.8):
    """Retrieves similar workflows based on a query string."""
    query_embedding = get_embeddings(query)
    if isinstance(query_embedding[0], list):
        query_embedding = query_embedding[0]
    query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
    
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT id, descriptions, workflow, 1 - (embedding <-> %s) AS similarity
        FROM workflows
        ORDER BY similarity DESC
        LIMIT %s;
    """, (query_embedding_str, top_k))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return [(id, desc, wf, sim) for id, desc, wf, sim in results if sim >= similarity_threshold]

# ================================
# Save Workflow to Database
# ================================

def save_workflow(descriptions: str, workflow_json: str):
    """
    Saves a workflow to the database along with its embedding.
    @Feature Save Workflow
    @Scenario Save workflow description, JSON structure, and embedding into the workflows table.
    """
    print(f"\n save_workflow()_Received (description) {descriptions}\n")
    descriptions = descriptions.strip()  # Clean leading/trailing whitespace
    embedding = get_embeddings(descriptions)
    if isinstance(embedding, list) and embedding and isinstance(embedding[0], list):
        embedding = embedding[0]
    embedding = normalize_embedding(embedding)
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    # print(f"\n save_workflow()_embedding_str {embedding_str}\n")
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workflows (descriptions, workflow, embedding) VALUES (%s, %s, %s)",
        (descriptions, workflow_json, embedding_str)
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"Workflow saved with description: {descriptions}")

# ============================================
# Embedding Functions and Normalization Methods
# ============================================

def get_embeddings(text: str) -> list:
    """
    Generate embeddings for a given text.
    @Feature Embedding Generation
    @Scenario Generate a normalized embedding vector for given text input.
    """
    embeddings = model.encode([text])
    return embeddings[0]

def normalize_embedding(embedding):
    """
    Normalize the embedding vector to unit length.
    @Feature Embedding Normalization
    @Scenario Ensure embedding vector is normalized; handle list and numpy types.
    """
    if isinstance(embedding, list):
        embedding = np.array(embedding)
    norm = np.linalg.norm(embedding)
    return (embedding / norm).tolist() if norm > 0 else embedding.tolist()

# Get embeddings from Hugging Face API
# def get_embeddings(text: str) -> list:
#     """Generates embeddings for a given text using Hugging Face API."""
#     response = client.feature_extraction(text, model="sentence-transformers/all-MiniLM-L6-v2")
#     return response.tolist()

# ====================================================
# Function to Generate and Store Node Embeddings
# ====================================================

def generate_and_store_node_embeddings(nodes: List[Dict], update_embeddings: bool = True) -> None:
    """
    @Feature Generate & Store Node Embeddings
    @Scenario Process each node and store input, output, tags, descriptions, SPO, and overall embeddings.
    Generate normalized embeddings for nodes and store them in PostgreSQL.
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        cur = conn.cursor()
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

    node_embeddings = []
    def format_embedding(emb: List[float]) -> str:
        # Ensure consistent vector formatting (e.g., "[1.0,2.0,...]")
        return '[' + ','.join(map(str, emb)) + ']'

    for node in nodes:
        try:
            input_text = ', '.join(node.get('input', []))
            output_text = ', '.join(node.get('output', []))
            tags_text = ', '.join(node.get('tags', []))
            description_text = ', '.join(node.get('description', []))
            spo = node.get('SPO', {})
            spo_text = f"{spo.get('subject', '')} {spo.get('predicate', '')} {spo.get('object', '')}"

            input_embedding = normalize_embedding(get_embeddings(input_text))
            output_embedding = normalize_embedding(get_embeddings(output_text))
            tags_embedding = normalize_embedding(get_embeddings(tags_text))
            description_embedding = normalize_embedding(get_embeddings(description_text))
            spo_embedding = normalize_embedding(get_embeddings(spo_text))
            overall_embedding = normalize_embedding(get_embeddings(
                f"{node.get('id', '')}: - input: {input_text} - output: {output_text} - tags: {tags_text} - description: {description_text} - SPO: {spo_text}"
            ))
            print(f"\noverall_embedding:overall_embedding\n")
        except Exception as e:
            logger.error(f"Error generating embeddings for node {node.get('id', 'unknown')}: {e}")
            continue
        
        print(f"\nGenerating embedding for node: {node['id']}")
        print(f"Input: {input_text}")
        print(f"Output: {output_text}")
        print(f"Tags: {tags_text}")
        print(f"Description: {description_text}")
        print(f"SPO: {spo_text}\n")

        node_embeddings.append((
            node.get('id'),
            format_embedding(input_embedding),
            format_embedding(output_embedding),
            format_embedding(tags_embedding),
            format_embedding(description_embedding),
            format_embedding(spo_embedding),
            format_embedding(overall_embedding)
        ))
    
    if update_embeddings:
        try:
            args_str = ','.join(
                cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)", item).decode('utf-8')
                for item in node_embeddings
            )
            cur.execute(
                "INSERT INTO node_embeddings (node_id, input_embedding, output_embedding, tags_embedding, description_embedding, spo_embedding, overall_embedding) VALUES " +
                args_str +
                " ON CONFLICT (node_id) DO UPDATE SET input_embedding = EXCLUDED.input_embedding, output_embedding = EXCLUDED.output_embedding, tags_embedding = EXCLUDED.tags_embedding, description_embedding = EXCLUDED.description_embedding, spo_embedding = EXCLUDED.spo_embedding, overall_embedding = EXCLUDED.overall_embedding;"
            )
        except Exception as e:
            logger.error(f"Error storing node embeddings: {e}")
            conn.rollback()
            raise
    else:
        logger.info("No embeddings stored because update_embeddings flag is FALSE")
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Node embeddings stored in batch.")

# ====================================================
# Batch Retrieval of Similar Nodes
# ====================================================
def retrieve_similar_nodes_batch(blueprint_steps: List[Dict], top_k: int = 5) -> Dict[str, List[Tuple]]:
    """
    @Feature High-Performance Workflow Node Matching
    @Scenario Retrieve Similar Nodes with Two-Stage Filtering
    Retrieve similar nodes using two-stage filtering.
    """
    if not blueprint_steps:
        logger.error("Blueprint steps cannot be empty")
        raise ValueError("Blueprint steps list is empty")

    all_input_embeddings = []
    all_output_embeddings = []
    all_tags_embeddings = []
    all_description_embeddings = []
    all_spo_embeddings = []
    mapping_keys = []

    for step in blueprint_steps:
        key = step["step"]
        mapping_keys.append(key)

        input_text = ', '.join(step.get('input', []))
        output_text = ', '.join(step.get('output', []))
        tags_text = ', '.join(step.get('tags', []))
        description_text = ', '.join(step.get('description', []))
        spo_text = f"{step.get('SPO', {}).get('subject', '')} {step.get('SPO', {}).get('predicate', '')} {step.get('SPO', {}).get('object', '')}"

        input_embedding = normalize_embedding(get_embeddings(input_text))
        output_embedding = normalize_embedding(get_embeddings(output_text))
        tags_embedding = normalize_embedding(get_embeddings(tags_text))
        description_embedding = normalize_embedding(get_embeddings(description_text))
        spo_embedding = normalize_embedding(get_embeddings(spo_text))

        all_input_embeddings.append(input_embedding)
        all_output_embeddings.append(output_embedding)
        all_tags_embeddings.append(tags_embedding)
        all_description_embeddings.append(description_embedding)
        all_spo_embeddings.append(spo_embedding)

        print(f"\n--- retrieve_similar_nodes_batch - Blueprint Step: {key} ---")
        print(f"Input Text: {input_text}")
        print(f"Output Text: {output_text}")
        print(f"Tags Text: {tags_text}")
        print(f"Description Text: {description_text}")
        print(f"SPO Text: {spo_text}")
        # print(f"Input Embedding (first 5): {input_embedding[:5] if input_embedding is not None else None}")
        # print(f"Output Embedding (first 5): {output_embedding[:5] if output_embedding is not None else None}")
        # print(f"Tags Embedding (first 5): {tags_embedding[:5] if tags_embedding is not None else None}")
        # print(f"Description Embedding (first 5): {description_embedding[:5] if description_embedding is not None else None}")
        # print(f"SPO Embedding (first 5): {spo_embedding[:5] if spo_embedding is not None else None}")

    def format_embeddings_for_sql(embeddings: List[List[float]]) -> List[str]:
        return [f'[{",".join(map(str, emb))}]' for emb in embeddings]

    formatted_input_embeddings = format_embeddings_for_sql(all_input_embeddings)
    formatted_output_embeddings = format_embeddings_for_sql(all_output_embeddings)
    formatted_tags_embeddings = format_embeddings_for_sql(all_tags_embeddings)
    formatted_description_embeddings = format_embeddings_for_sql(all_description_embeddings)
    formatted_spo_embeddings = format_embeddings_for_sql(all_spo_embeddings)

    conn = pool.getconn()
    results = []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM retrieve_similar_nodes_twostep_batch(
                %s::vector(1024)[],
                %s::vector(1024)[],
                %s::vector(1024)[],
                %s::vector(1024)[],
                %s::vector(1024)[],
                %s::int
            )
        """, (formatted_input_embeddings, formatted_output_embeddings, formatted_tags_embeddings, formatted_description_embeddings, formatted_spo_embeddings, top_k))
        results = cur.fetchall()
        logger.info(f"Retrieved {len(results)} similar node results")
        print(f"\n--- retrieve_similar_nodes_batch - SQL Query Results: {results} ---\n")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error retrieving similar nodes: {str(e)}")
        raise
    finally:
        cur.close()
        pool.putconn(conn)

    similar_nodes_by_query = {key: [] for key in mapping_keys}
    # SQL returns 8 columns: query_idx, node_id, input_sim, output_sim, tags_sim, desc_sim, spo_sim, total_score
    for row in results:
        if len(row) != 8:
            logger.warning(f"Unexpected number of columns in result row: {row}")
            continue
        query_idx, node_id, input_sim, output_sim, tags_sim, desc_sim, spo_sim, total_score = row
        if query_idx >= len(mapping_keys):
            logger.warning(f"Invalid query index {query_idx} for {len(mapping_keys)} subtasks")
            continue
        key = mapping_keys[query_idx]
        node = next((n for n in AVAILABLE_NODES if n.get('id') == node_id), None)
        if node:
            similar_nodes_by_query[key].append((node, total_score, input_sim, output_sim, tags_sim, desc_sim, spo_sim, total_score))
            logger.debug(f"Node {node_id} for '{key}': input_sim={input_sim}, output_sim={output_sim}, total_score={total_score}")
    print(f"---------similar_nodes_by_query--RETURNED----{similar_nodes_by_query}")
    return similar_nodes_by_query

# ====================================================
# Filter Nodes by Embedding Batch with AI Final Verification
# ====================================================
def filter_nodes_by_embedding_batch(blueprint_steps: List[Dict], nodes: List[Dict], top_k: int = 3) -> Dict[str, List[Dict]]:
    """
    @Feature High-Performance Workflow Node Matching
    @Scenario Filter Nodes with AI Verification
    Filter nodes with AI verification based on blueprint steps.
    This function uses a two-stage candidate retrieval and then employs an AI-based
    final verification. It also tracks and logs missing node scenarios.
    """
    global AVAILABLE_NODES
    AVAILABLE_NODES = nodes

    missing_nodes_list = []

    # print(f"-------blueprint_steps-------{blueprint_steps}")
    print(f"-------blueprint_steps-TYPE------{type(blueprint_steps)}")
    # print(f"-------AVAILABLE_NODES-------{AVAILABLE_NODES}")
    print(f"-------AVAILABLE_NODES-TYPE------{type(AVAILABLE_NODES)}")
    similar_nodes_by_query = retrieve_similar_nodes_batch(blueprint_steps, top_k=top_k)
    print(f"-------similar_nodes_by_query-------{similar_nodes_by_query}")
    print(f"-------similar_nodes_by_query-TYPE------{type(similar_nodes_by_query)}")

    for i, step in enumerate(blueprint_steps):
        key = step["step"]
        candidates = similar_nodes_by_query.get(key, [])
        print(f"\n--- filter_nodes_by_embedding_batch - Candidates for subtask '{key}': ---")
        for candidate_tuple in candidates:
            candidate, score, in_sim, out_sim, tag_sim, desc_sim, spo_sim, _ = candidate_tuple
            print(f"Node: {candidate.get('id')}, Input: {candidate.get('input')}, "
                  f"Output: {candidate.get('output')}, SPO: {candidate.get('SPO')}, "
                  f"Similarity: {score:.4f}")

    filtered_nodes_map = {}

    # Process each blueprint step
    for step in blueprint_steps:
        key = step['step']
        candidates = similar_nodes_by_query.get(key, [])
        if not candidates:
            logger.warning(f"No nodes found for subtask '{key}'")
            missing_nodes_list.append({
                "subtask": key,
                "Function_Inputs": step.get('input', []),
                "Function_Output": step.get('output', []),
                "Function_Description": step.get('description', ''),
            })
            filtered_nodes_map[key] = []
            continue

        # candidate_list = "\n".join([
        #     f"node: {node['id']}: input_sim={in_sim:.4f}, output_sim={out_sim:.4f}, "
        #     f"tags_sim={tag_sim:.4f}, desc_sim={desc_sim:.4f}, spo_sim={spo_sim:.4f}, score={score:.4f}"
        #     for node, score, in_sim, out_sim, tag_sim, desc_sim, spo_sim, _ in candidates
        # ])
        candidate_list = "\n".join([
            f"node: {node['id']}: input={node['input']}, output={node['output']}, tags={node['tags']}, description={node['description']}, SPO={node['SPO']}, score={score:.4f}"
            for node, score,*_ in candidates
        ])
        logger.debug(f"Candidate list for step '{key}':\n{candidate_list}")

        # Use the provided ai_prompt (unchanged) for AI verification.
        ai_prompt = f"""
        <Subtask_Details>
            Subtask Name: "{step['step']}"
            Input: {step.get('input', [])}
            Output: {step.get('output', [])}
            Tags: {step.get('tags', [])}
            Description: {step.get('description', '')}
            SPO: {step.get('SPO', '')}
        </Subtask_Details>
        <Candidate_Nodes_List>
        {candidate_list}
        </Candidate_Nodes_List>
        <Matching_Guidelines>
            1. Return ONLY the exact node ID(s) from the candidate list as plain strings (e.g., "analyze_image", "Blog_Writer"). Do NOT include any prefixes or extra text.
            2. Evaluate each candidate node based on:
            - An exact, partially compatible, or semantically equivalent match of the "input" and "output" lists.
            - Semantic alignment of "tags" and "description" (recognizing synonyms; for example, treat "video transcript" and "transcript", "url" as "website_url", as equivalent).
            - If available, any meta information should be used for additional guidance.
            3. Prioritize the candidate that best meets these criteria and is most semantically relevant to the subtask.
            4. If no candidate meets the criteria, return MISSING_NODE.
        </Matching_Guidelines>
        <Expected_JSON_Output_Format>
            Return ONLY a JSON object in one of these forms:
            {{"SELECTED_NODE": ["<exact_node_id1>"]}}
            OR, if no candidate node is suitable:
            {{"MISSING_NODE": ["<subtask_name>"]}}
        </Expected_JSON_Output_Format>
        FINAL_SELECTION_NODE:
        Return ONLY the exact node ID(s) without any additional formatting.
        """
        print(f"\n----ai_prompt----- filter_nodes_by_embedding_batch (step: {key}): {ai_prompt}\n")

        try:
            # Call the AI system with the unmodified prompt.
            ai_response = Ask_AI(ai_prompt, context="Return valid JSON")
            print(f"\nai_response filter_nodes_by_embedding_batch (step: {key}): {ai_response}\n")

            logger.info(f"AI response for subtask '{key}': {ai_response}")
            parsed_response = json.loads(ai_response)
            if "SELECTED_NODE" in parsed_response:
                selected_node_ids = parsed_response["SELECTED_NODE"]
                selected_nodes = [node for node, *_ in candidates if node['id'] in selected_node_ids]
                filtered_nodes_map[key] = selected_nodes
            elif "MISSING_NODE" in parsed_response:
                logger.warning(f"AI returned MISSING_NODE for subtask '{key}'")
                missing_nodes_list.append({
                    "subtask": key,
                    "Function_Inputs": step.get('input', []),
                    "Function_Output": step.get('output', []),
                    "Function_Description": step.get('description', ''),
                })
                filtered_nodes_map[key] = []
            else:
                logger.warning(f"AI response did not match expected format for subtask '{key}'")
                missing_nodes_list.append({
                    "subtask": key,
                    "Function_Inputs": step.get('input', []),
                    "Function_Output": step.get('output', []),
                    "Function_Description": step.get('description', ''),
                })
                filtered_nodes_map[key] = []
        except Exception as e:
            logger.error(f"Error processing AI response for subtask '{key}': {e}")
            missing_nodes_list.append({
                "subtask": key,
                "Function_Inputs": step.get('input', []),
                "Function_Output": step.get('output', []),
                "Function_Description": step.get('description', ''),
            })
            filtered_nodes_map[key] = []

    if missing_nodes_list:
        logger.info(f"Missing nodes detected for subtasks: {json.dumps(missing_nodes_list, indent=2)}")

    return filtered_nodes_map

# AI interaction function
def Ask_AI(prompt: str, context: str = "Follow all instructions completely") -> str:
    """Interacts with AI model to get a response."""
    if not prompt:
        return "Error: 'prompt' is required."
    messages = [("system", prompt), ("human", f"<context>\n{context}\n</context>")]
    response = llm.invoke(messages)
    raw_response = response.content if response else "Error: Failed to generate response."
    if "Return valid JSON" in context:
        import re
        json_match = re.search(r'\{.*\}|\[.*\]', raw_response, re.DOTALL)
        return json_match.group(0) if json_match else f"Error: Invalid JSON - {raw_response}"
    return raw_response

# Validate nodes against schema
def validate_nodes(nodes: List[Dict]) -> List[Dict]:
    """Validates nodes against the defined schema."""
    try:
        validate(instance=nodes, schema=NODE_SCHEMA)
        return nodes
    except ValidationError as e:
        print(f"Validation error: {e}")
        return AVAILABLE_NODES[:len(nodes)]

# Agent state definition
class AgentState(TypedDict):
    task: str
    allowed_nodes: List[str]
    available_nodes: List[Dict]
    subtasks: List[str]
    subtask_sequence: List[str]
    subtask_node_map: Dict[str, List[Dict]]
    plan: List[Dict]
    context: str
    current_step: int
    workflow_valid: Optional[bool]
    final_workflow: Optional[Dict]
    evaluation: dict
    replan_attempts: int

# Initialize agent state
def initialize_state(state: AgentState):
    """Initializes the agent state with default values."""
    state["available_nodes"] = AVAILABLE_NODES
    state["subtasks"] = []
    state["subtask_sequence"] = []
    state["subtask_node_map"] = {}
    state["plan"] = []
    state["context"] = ""
    state["workflow_valid"] = None
    state["current_step"] = 0
    state["evaluation"] = {}
    state["replan_attempts"] = 0
    state["final_workflow"] = {}
    return state

# Decompose task into subtasks
def decompose_task(state: AgentState):
    """Decomposes the main task into distinct, logically sequenced subtasks with meta-level insights."""
    prompt = f"""
    Given the task: "{state['task']}", perform the following steps:

    1. Identify the key objectives and specific requirements by understanding the overall intent and context of the task. Remove any duplicate or redundant information.
    2. Decompose the task into clear, meaningful subtasks that directly support the primary objective.
       - Do not split the process into trivial or overly granular steps.
       - Exclude non-essential actions unless explicitly required.
    3. For each subtask, generate 3 diverse, high-quality examples that showcase distinct approaches with minimal overlap.
    4. Analyze these examples to extract a meta-pattern using the interrogatives (Who, What, When, Where, Why, How) that encapsulates the task's core components and context.
    5. Consolidate the subtasks into a single, logically ordered sequence, ensuring that similar actions are not repeated consecutively.

    Return ONLY a valid Format JSON object with EXACTLY these keys:
       - "subtasks": a list of subtask names, each reflecting a distinct, meaningful step.
       - "sequence": a list detailing the execution order of these subtasks, with no consecutive repetition of the same node type.

    Do NOT include any extra tokens, markdown, or formatting (such as __start__ or __end__) in your output.
    """
    response = Ask_AI(prompt, context="Return valid JSON") 
    # print(f"\nAI response for decompose_task: {json.dumps(response, indent=2)}\n")
    print(f"\nAI response for decompose_task: {response}\n")
    try:
        result = json.loads(response)
        state["subtasks"] = result["subtasks"]
        state["subtask_sequence"] = result["sequence"]
    except Exception as e:
        print(f"Error parsing decompose_task response: {e}")
        state["subtasks"] = state["task"].split(". ")
        state["subtask_sequence"] = state["subtasks"]
    return state

# Creates an initial blueprint for subtasks that exactly follows the node embedding format.
def create_initial_subtask_workflow(state: AgentState) -> AgentState:
    prompt = f"""
    Given the task: "{state['task']}"
    And the identified subtasks: {json.dumps(state['subtasks'])}
    
    For each subtask, generate a blueprint that strictly follows the node format. Each blueprint dictionary must include:
    
    - "step": A string representing the subtask name.
    - "input": A list of input parameter names as strings (e.g., ["prompt", "context"]). Do not provide objects or key/value pairs.
    - "output": A list of output parameter names as strings (e.g., ["ai_response", "generated_text", "AI"]).
    - "tags": A list of exactly 3 to 5 tags (strings) that describe the node's domain and function.
    - "description": A list of three description strings where:
         * The first line clearly states the node's primary function and theme.
         * The second line explains the key benefits it provides.
         * The third line offers additional context or typical use cases.
    - "SPO": A dictionary with:
        * "subject" → The core entity performing the action (e.g., "AI-powered classifier", "Automated data processor").
        * "predicate" → A strong action verb describing what it does (e.g., "extracts", "analyzes", "optimizes").
        * "object" → The intended purpose or benefit (e.g., "to improve decision-making", "for automation and efficiency").

    Return ONLY a JSON list of dictionaries with the keys: "step", "input", "output", "tags", "description", "SPO".
    Do NOT include any additional text or explanations.
    """
    response = Ask_AI(prompt, context="Return valid JSON")
    print(f"\nAI response for create_initial_subtask_workflow (blueprint): {response}\n")
    try:
        state["plan"] = json.loads(response)
        for step in state["plan"]:
            step["description_embed"] = f"{step['step']}: - input: {step['input']} - output: {step['output']} - tags: {', '.join(step.get('tags', []))} - description: {step['description']} - SPO: {step.get('SPO', '')}"
    except Exception as e:
        print(f"Error parsing create_initial_subtask_workflow response: {e}")
        state["plan"] = [{"step": s,
                            "input": [f"param1_for_{s}", f"param2_for_{s}"],
                            "output": [f"result1_for_{s}"],
                            "tags": [f"tag1_for_{s}", f"tag2_for_{s}", f"tag3_for_{s}"],
                            "description": [f"Main function for {s}", f"Benefit for {s}", f"Context for {s}"],
                            "SPO": {"subject": f"Node for {s}", "predicate": "performs", "object": f"the function of {s}"}
                           } for s in state["subtasks"]]
    return state

# Generates a batch plan for the workflow
def generate_plan_batch(state: AgentState):
    """Generates a batch plan for the workflow."""
    state = create_initial_subtask_workflow(state)

    state["subtask_sequence"] = [step["step"] for step in state["plan"]]
    print(f"\n--- subtask_sequence (generate_plan_batch()) (After create_initial_subtask_workflow()) {state['subtask_sequence']}---\n")
    

    # Update to use the blueprint steps directly for filtering
    state["subtask_node_map"] = filter_nodes_by_embedding_batch(state["plan"], state["available_nodes"])

    print(f"\n--- subtask_node_map (generate_plan_batch()) (FilteredNodes(state['plan'])) {state['subtask_node_map']}---\n")
    plan = []
    for step in state["plan"]:
        nodes = state["subtask_node_map"].get(step["step"], [])
        if nodes:
            node_entry = {"node_id": nodes[0]["id"], "inputs": nodes[0]["input"], "output": nodes[0]["output"]}
            plan.append(node_entry)
        else:
            print(f"Warning: No nodes for '{step['step']}'")

    state["plan"] = plan
    print(f"\n---------Printing the Last Plan (generate_plan_batch()) {plan}---------\n")
    return state

# Execute workflow step
def execute_step(state: AgentState):
    """Executes the current step in the workflow plan."""
    partial_plan = state["plan"][:state["current_step"] + 1]
    # print(f"Partial Workflow at step {state['current_step'] + 1}:\n{json.dumps(partial_plan, indent=4)}")
    state["final_workflow"] = generate_workflow_from_plan(state, plan=partial_plan)
    state["current_step"] += 1
    state["workflow_valid"] = True
    return state

# Finalize workflow generation (changed)
def finalize(state: AgentState):
    """Finalizes the workflow generation process."""
    state["final_workflow"] = generate_workflow_from_plan(state)
    return state

# Create compiled node for workflow
def create_compiled_node(step: Dict, state: AgentState) -> Dict:
    """Creates a compiled node for the workflow."""
    return {
        "id": step["node_id"],
        "type": "runnable",
        "data": {"id": ["langgraph", "graph", "state", "CompiledStateGraph"], "name": step["node_id"]},
        "inputs": {k: "" for k in step.get("inputs", [])},
        "output": {k: "" for k in step.get("output", [])}
    }

# Create callable node for workflow
def create_callable_node(step: Dict, state: AgentState) -> Dict:
    """Creates a callable node for the workflow."""
    return {
        "id": step["node_id"],
        "type": "runnable",
        "data": {"id": ["langgraph", "utils", "runnable", "RunnableCallable"], "name": step["node_id"]},
        "inputs": {k: "" for k in step.get("inputs", [])},
        "output": {k: "" for k in step.get("output", [])}
    }

# Generate workflow from plan (changed)
def generate_workflow_from_plan(state: AgentState, plan: Optional[List[Dict]] = None, top_level: bool = True) -> Dict:
    """Convert the plan into a structured workflow with nodes and edges, including sub-workflows."""
    if plan is None:
        plan = state["plan"]
    # --- Ensure special nodes are present in the plan ---
    if not any(step["node_id"] == "__start__" for step in plan):
        plan.insert(0, {"node_id": "__start__", "inputs": {}, "output": {}})
    if not any(step["node_id"] == "__end__" for step in plan):
        plan.append({"node_id": "__end__", "inputs": {}, "output": {}})
    
    # --- Build nodes list in fixed order ---
    nodes_list = [create_callable_node(step, state) for step in plan if step.get("node_id") not in ["__start__", "__end__"]]
    # Special nodes
    start_node = {"id": "__start__", "type": "schema", "data": "__start__"}
    end_node = {"id": "__end__", "type": "schema", "data": "__end__"}
    # Final nodes order: callable nodes, then special nodes.
    nodes_list = nodes_list + [start_node, end_node]

    edges_list = []
    for i in range(len(plan) - 1):
        edge = {"source": plan[i]["node_id"], "target": plan[i + 1]["node_id"]}
        edges_list.append(edge)

    workflow_json = {
        "state": {"mainstate": None, "inputstate": None, "outputstate": None},
        "nodes": nodes_list,
        "edges": edges_list
    }

    return workflow_json

# Create planning workflow
def create_planning_workflow():
    """Creates the planning workflow using StateGraph."""
    workflow = StateGraph(AgentState)
    workflow.add_node("init", initialize_state)
    workflow.add_node("decompose", decompose_task)
    workflow.add_node("planning", generate_plan_batch)
    workflow.add_node("execute", execute_step)
    workflow.add_node("finalize", finalize)
    
    workflow.add_edge("init", "decompose")
    workflow.add_edge("decompose", "planning")
    workflow.add_edge("planning", "execute")
    
    def decide_next_step(state: AgentState) -> Literal["planning", "execute", "finalize"]:
        if state.get("workflow_valid") is False:
            return "planning"
        elif state["current_step"] >= len(state["plan"]):
            return "finalize"
        return "execute"
    
    workflow.add_conditional_edges("execute", decide_next_step, {"planning": "planning", "execute": "execute", "finalize": "finalize"})
    workflow.set_entry_point("init")
    return workflow.compile()

# Generate workflow from user task
def generate_workflow(user_task, allowed_nodes: Optional[List[str]] = None):
    """Generates a workflow based on user task."""
    similar_workflows = retrieve_similar_workflow(user_task)
    if similar_workflows:
        return json.dumps(similar_workflows[0][2], indent=4)
    
    initial_state = {
        "task": user_task,
        "allowed_nodes": allowed_nodes,
        "available_nodes": [],
        "subtasks": [],
        "subtask_sequence": [],
        "subtask_node_map": {},
        "plan": [],
        "context": "",
        "current_step": 0,
        "workflow_valid": None,
        "evaluation": {},
        "replan_attempts": 0,
        "final_workflow": {}
    }
    generate_and_store_node_embeddings(AVAILABLE_NODES)
    planning_workflow = create_planning_workflow()
    final_state = planning_workflow.invoke(initial_state, {"recursion_limit": 100})
    final_workflow_json = json.dumps(final_state.get('final_workflow', {}), indent=4)
    print(f"\n ---user_task--- {user_task} \n")
    save_workflow(user_task, final_workflow_json)
    return final_workflow_json

# Example usage
# UserTaskQuery = """
# i want to analyze the image and summarize the scence and create the blog content. 
# """
UserTaskQuery = """
i want to scrape the websites, extract keywords, summarize the content and write blog.
"""
# UserTaskQuery = """
# i want to scrape the websites, extract keywords, summarize the content and write SEO optimized blog. 
# """
# final_workflow = generate_workflow('''I need a workflow that processes a YouTube video for marketing analysis. which summerize the video content and generate keywords from the transcript and in the end write blog''')

final_workflow = generate_workflow(UserTaskQuery)

print(f"Final Workflow:\n{final_workflow}")