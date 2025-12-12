from typing import List, Dict, Union, Optional, Tuple
from pydantic import BaseModel, validator, ValidationError
import numpy as np
import json
import logging
import re, os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from llm_ai import Ask_AI
from embedding_util import get_embeddings, normalize_embedding
from db_connection import pool
from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES

load_dotenv()

# Define your desired directory
# Define the local path where the model was stored

local_model_path = os.getenv("LOCAL_MODEL_PATH")
model = SentenceTransformer(local_model_path)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ============================
# Common Schema + Validation
# ============================

class SPO(BaseModel):
    subject: str
    predicate: str
    object: str

class BlueprintStep(BaseModel):
    step: str
    input: List[str]
    output: List[str]
    tags: List[str]
    description: List[str]
    SPO: List[str]  # Change to List[str] to match embedding pattern

    @validator("input", "output", "tags", pre=True)
    def validate_lists(cls, v):
        return v if isinstance(v, list) else []
    
    @validator("SPO", pre=True, always=True)
    def validate_spo(cls, v):
        if isinstance(v, dict):
            return [v.get("subject", ""), v.get("predicate", ""), v.get("object", "")]
        elif isinstance(v, list):
            return v
        return []
    
class Node(BaseModel):
    id: str
    input: List[str]
    output: List[str]
    tags: List[str]
    description: List[str]
    SPO: List[str]  # Change to List[str] to match embedding pattern


# ============================
# Prompt Construction
# ============================

# @Feature: Prompt Safety and Robustness
# @Scenario: Generate schema-compliant, injection-safe AI prompt

def filter_ai_prompt(step: BlueprintStep, candidate_list: str) -> str:
    print(f"\n--- filter_ai_prompt - candidate_list: {candidate_list} ---\n")
    try:
        spo_text = " ".join(step.SPO)  # Join the SPO list into a single string
        
        prompt = f"""
        <Subtask_Details>
            Subtask Name: "{step.step}"
            Input: {step.input}
            Output: {step.output}
            Tags: {step.tags}
            Description: {step.description}
            SPO: {spo_text}
        </Subtask_Details>
        <Candidate_Nodes_List>
        {candidate_list}
        </Candidate_Nodes_List>
        <Matching_Guidelines>
            1. Return ONLY the exact node ID(s) from the candidate list as plain strings (e.g., "analyze_image").
            2. Evaluate matches based on semantic similarity of inputs, outputs, tags, descriptions, and SPO fields.
            3. Prioritize exact or semantically relevant or semantically equivalent match.
            4. If no good match exists, return MISSING_NODE.
        </Matching_Guidelines>
        <Expected_JSON_Output_Format>
            Return ONLY:
            {{"SELECTED_NODE": ["<node_id>"]}} OR {{"MISSING_NODE": ["<subtask_name>"]}}
        </Expected_JSON_Output_Format>
        FINAL_SELECTION_NODE:
        """
        return prompt
    except Exception as e:
        logger.exception("Prompt construction failed")
        raise

# ============================
# AI Output Parsing
# ============================

# @Feature: AI Output Integrity
# @Scenario: Parse and validate AI's JSON response format safely

def parse_ai_response(ai_response: str, step_key: str) -> Union[List[str], str]:
    try:
        parsed = json.loads(ai_response)
        if "SELECTED_NODE" in parsed:
            return parsed["SELECTED_NODE"]
        elif "MISSING_NODE" in parsed:
            return "MISSING_NODE"
        else:
            raise ValueError(f"Unexpected keys in AI response: {parsed.keys()}")
    except Exception as e:
        logger.warning(f"Failed to parse AI response for step '{step_key}': {e}")
        return "MISSING_NODE"

# ============================
# AI Call Abstraction
# ============================

# @Feature: AI Integration
# @Scenario: Query LLM with context-rich prompts and handle output consistently

# def Ask_AI(prompt: str, context: str = "Return valid JSON") -> str:
#     messages = [("system", prompt), ("human", f"<context>\n{context}\n</context>")]
#     response = llm.invoke(messages)
#     raw_response = response.content if response else "{}"
#     match = re.search(r'\{.*\}|\[.*\]', raw_response, re.DOTALL)
#     return match.group(0) if match else "{}"

# ====================================================
# Filter Nodes by Embedding Batch with AI Final Verification
# ====================================================
# @Feature: AI-Driven Node Matching
# @Scenario: Match each blueprint step to best candidate node or log as missing

def filter_nodes_by_embedding_batch(blueprint_steps: List[Dict], nodes: List[Dict],top_k: int = 3) -> Dict[str, List[Dict]]:
    global AVAILABLE_NODES
    # AVAILABLE_NODES = [Node(**n).dict() for n in nodes]
    AVAILABLE_NODES = [
        Node(
            **{
                **n,
                "SPO": [n["SPO"]["subject"], n["SPO"]["predicate"], n["SPO"]["object"]]
                if isinstance(n.get("SPO"), dict) else n.get("SPO", [])
            }
        ).dict()
        for n in nodes
    ]
    # parsed_steps = [BlueprintStep(**step) for step in blueprint_steps]
    parsed_steps = [
        BlueprintStep(
            **{
                **step,
                "SPO": [step["SPO"]["subject"], step["SPO"]["predicate"], step["SPO"]["object"]]
                if isinstance(step.get("SPO"), dict) else step.get("SPO", [])
            }
        )
        for step in blueprint_steps
    ]
    similar_nodes_by_query = retrieve_similar_nodes_batch(parsed_steps, top_k)
    filtered_nodes_map = {}
    missing_nodes_list = []

    for step in parsed_steps:
        key = step.step
        candidates = similar_nodes_by_query.get(key, [])
        print(f"--- filter_nodes_by_embedding_batch - Candidates for step '{key}': {candidates} ---")
        if not candidates:
            logger.warning(f"No candidates for step {key}")
            missing_nodes_list.append(step.dict())
            filtered_nodes_map[key] = []
            continue

        # candidate_list = "\n".join([
        #     f"node: {node['id']}: input={input:.4f}, output={output:.4f}, score={score:.4f}"
        #     for node, score, input, output, *_ in candidates
        # ])

        # candidate_list = "\n".join([
        #     f"node: {node['id']}: input={input:.4f}, output={output:.4f}, tags={', '.join(node['tags'])}, description={', '.join(node['description'])}, SPO={', '.join(node['SPO'])}, score={score:.4f}"
        #     for node, score, input, output, *_ in candidates
        # ])

        # candidate_list = "\n".join([ # Not woriking
        #     f"node: {node['id']}: input={node['input']}, output={node['output']}, tags={node['tags']}, description={node['description']}, SPO={node['SPO']}, score={score:.4f}"
        #     for node, score, input, output, *_ in candidates
        # ])

        # candidate_list = "\n".join([
        #     f"node: {node['id']}: input={', '.join(node['input'])}, output={', '.join(node['output'])}, tags={', '.join(node['tags'])}, description={' | '.join(node['description'])}, SPO={' '.join(node['SPO'])}"
        #     for node, *_ in candidates
        # ])
        candidate_list = "\n".join([
            f"node: {node['id']}: input={node['input']}, output={node['output']}, tags={node['tags']}, description={node['description']}, SPO={node['SPO']}, score={score:.4f}"
            for node, score,*_ in candidates
        ])

        print(f"\n--- filter_nodes_by_embedding_batch - Candidate List for step '{key}': {candidate_list} ---\n")
        # Select the best candidate node for each step
        ai_prompt = filter_ai_prompt(step, candidate_list)
        print(f"\n--- filter_nodes_by_embedding_batch - AI Prompt for step '{key}': {ai_prompt} ---\n")
        ai_response = Ask_AI(ai_prompt)
        print(f"\n--- filter_nodes_by_embedding_batch - AI Response for step '{key}': {ai_response} ---\n")
        result = parse_ai_response(ai_response, key)

        if result == "MISSING_NODE":
            missing_nodes_list.append(step.dict())
            filtered_nodes_map[key] = []
        else:
            selected_nodes = [node for node, *_ in candidates if node['id'] in result]
            filtered_nodes_map[key] = selected_nodes

    if missing_nodes_list:
        logger.info(f"Missing nodes: {json.dumps(missing_nodes_list, indent=2)}")

    return filtered_nodes_map

# ====================================================
# Batch Retrieval of Similar Nodes
# ====================================================
def retrieve_similar_nodes_batch(blueprint_steps: List[BlueprintStep], top_k: int = 5) -> Dict[str, List[Tuple]]:
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
        key = step.step  # Use dot notation to access the 'step' attribute
        mapping_keys.append(key)

        input_text = ', '.join(step.input)
        output_text = ', '.join(step.output)
        tags_text = ', '.join(step.tags)
        description_text = ', '.join(step.description)
        spo_text = ' '.join(step.SPO)

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

