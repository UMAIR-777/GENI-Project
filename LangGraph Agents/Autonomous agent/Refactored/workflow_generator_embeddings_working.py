from typing import TypedDict, List, Dict, Tuple, Literal, Optional
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
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Define your desired directory
# Define the local path where the model was stored

local_model_path = "./downloaded/sentence_transformers/bge-m3/BAAI_bge-m3"
# Load the model from the local directory
model = SentenceTransformer(local_model_path)
llm = ChatGroq(temperature=0, model="llama-3.3-70b-versatile")

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

# Database setup with batch stored procedures
def setup_database():
    """Sets up the PostgreSQL database with necessary tables and stored procedures."""
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="unicorn",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    # Enable vector extension for embedding storage
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    # Create node_embeddings table to store node_id, input_embedding, output_embedding, tags_embedding, description_embedding, spo_embedding, overall_embedding
    cur.execute("""
        CREATE TABLE IF NOT EXISTS node_embeddings (
            node_id TEXT PRIMARY KEY,
            input_embedding VECTOR(1024),
            output_embedding VECTOR(1024),
            tags_embedding VECTOR(1024),
            description_embedding VECTOR(1024),
            spo_embedding VECTOR(1024),
            overall_embedding VECTOR(1024)
        )
    """)
    # Create workflows table to store saved workflows
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            workflow JSONB NOT NULL,
            embedding VECTOR(1024) NOT NULL
        );
    """)
    
    # Create stored procedure for batch embedding storage
    cur.execute("""
        CREATE OR REPLACE PROCEDURE store_node_embeddings(
            node_data node_embeddings[]
        )
        LANGUAGE plpgsql
        AS $$ 
        BEGIN
            TRUNCATE TABLE node_embeddings;
            INSERT INTO node_embeddings SELECT * FROM unnest(node_data);
            COMMIT;
        END;
        $$;
    """)
    
    cur.execute("""
    CREATE OR REPLACE FUNCTION retrieve_similar_nodes_batch(
        query_embeddings VECTOR(1024)[],
        top_k INT
    ) RETURNS TABLE (
        query_index INT,
        node_id TEXT,
        similarity FLOAT
    ) LANGUAGE plpgsql AS $$
    BEGIN
        RETURN QUERY
        WITH query_embeddings_with_index AS (
            SELECT (idx)::INT AS query_index, embedding
            FROM unnest(query_embeddings) WITH ORDINALITY AS t(embedding, idx)
        ),
        ranked AS (
            SELECT
                q.query_index,
                n.node_id,
                1 - (n.overall_embedding <=> q.embedding) AS similarity,  -- Changed to overall_embedding
                ROW_NUMBER() OVER (PARTITION BY q.query_index ORDER BY (n.overall_embedding <=> q.embedding) ASC) AS rank  -- Changed to overall_embedding
            FROM query_embeddings_with_index q
            CROSS JOIN node_embeddings n
        )
        SELECT
            ranked.query_index,
            ranked.node_id,
            ranked.similarity
        FROM ranked
        WHERE ranked.rank <= top_k
        AND ranked.query_index <= array_length(query_embeddings, 1);
    END;
    $$;
    """)

    cur.execute("""
    CREATE OR REPLACE FUNCTION retrieve_similar_nodes_twostep_batch(
        query_overall_embeddings VECTOR(1024)[],
        query_input_embeddings VECTOR(1024)[],
        query_output_embeddings VECTOR(1024)[],
        query_tags_embeddings VECTOR(1024)[],
        query_description_embeddings VECTOR(1024)[],
        query_spo_embeddings VECTOR(1024)[],
        top_k INT
    ) RETURNS TABLE (
        query_index INT,
        node_id TEXT,
        overall_similarity FLOAT,
        input_similarity FLOAT,
        output_similarity FLOAT,
        tags_similarity FLOAT,
        description_similarity FLOAT,
        spo_similarity FLOAT
    ) LANGUAGE plpgsql AS $$
    BEGIN
        RETURN QUERY
        WITH query_embeddings_with_index AS (
            SELECT
                idx AS query_index,
                overall,
                input,
                output,
                tags,
                description,
                spo
            FROM unnest(
                query_overall_embeddings,
                query_input_embeddings,
                query_output_embeddings,
                query_tags_embeddings,
                query_description_embeddings,
                query_spo_embeddings
            ) WITH ORDINALITY AS t(overall, input, output, tags, description, spo, idx)
        ),
        first_pass AS (
            SELECT
                q.query_index,
                n.node_id,
                1 - (n.overall_embedding <=> q.overall) AS overall_similarity,
                q.input,
                q.output,
                q.tags,
                q.description,
                q.spo
            FROM query_embeddings_with_index q
            CROSS JOIN node_embeddings n
            WHERE 1 - (n.overall_embedding <=> q.overall) >= 0.8
        ),
        second_pass AS (
            SELECT
                fp.query_index,
                fp.node_id,
                fp.overall_similarity,
                1 - (n.input_embedding <=> fp.input) AS input_similarity,
                1 - (n.output_embedding <=> fp.output) AS output_similarity,
                1 - (n.tags_embedding <=> fp.tags) AS tags_similarity,
                1 - (n.description_embedding <=> fp.description) AS description_similarity,
                1 - (n.spo_embedding <=> fp.spo) AS spo_similarity,
                ROW_NUMBER() OVER (
                    PARTITION BY fp.query_index 
                    ORDER BY fp.overall_similarity DESC
                ) AS rank
            FROM first_pass fp
            JOIN node_embeddings n ON fp.node_id = n.node_id
            WHERE
                1 - (n.input_embedding <=> fp.input) >= 0.8 AND
                1 - (n.output_embedding <=> fp.output) >= 0.8 AND
                1 - (n.tags_embedding <=> fp.tags) >= 0.8 AND
                1 - (n.description_embedding <=> fp.description) >= 0.8 AND
                1 - (n.spo_embedding <=> fp.spo) >= 0.8
        )
        SELECT
            sp.query_index,        -- Explicitly qualified
            sp.node_id,
            sp.overall_similarity,
            sp.input_similarity,
            sp.output_similarity,
            sp.tags_similarity,
            sp.description_similarity,
            sp.spo_similarity
        FROM second_pass sp
        WHERE sp.rank <= top_k;
    END;
    $$;
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Database setup completed with batch stored procedures.")

# Call setup
setup_database()

# Updated AVAILABLE_NODES with detailed descriptions in list format
AVAILABLE_NODES = [
    {
        "id": "analyze_image",
        "input": ["image_file", "prompt"],
        "output": ["image_analysis"],
        "tags": ["Image Analysis", "AI", "Computer Vision"],
        "description": [
            "Analyzes an image using advanced AI models.",
            "Provides detailed insights including object detection and scene interpretation.",
            "Ideal for automated image classification and visual content assessment."
        ],
        "SPO": {
            "subject": "Automated image analysis tool",
            "predicate": "analyzes images using AI models",
            "object": "for object detection, scene interpretation, and visual content assessment"
        }
    },
    {
        "id": "website_scraper",
        "input": ["website_url"],
        "output": ["website_scraped_content"],
        "tags": ["Web Scraping", "Data Extraction", "Scraping"],
        "description": [
            "Scrapes content from websites by retrieving and parsing webpage data.",
            "Extracts structured information for further analysis and research.",
            "Suitable for data mining and competitive intelligence tasks."
        ],
        "SPO": {
            "subject": "Automated web scraper",
            "predicate": "extracts and structures online content",
            "object": "for research, data mining, and competitive intelligence"
        }
    },
    {
        "id": "analyze_video",
        "input": ["video_file_url", "prompt", "video_model"],
        "output": ["video_analysis"],
        "tags": ["Video Analysis", "AI", "Multimedia"],
        "description": [
            "Analyzes video content using specialized AI models.",
            "Extracts insights and generates detailed analytical results.",
            "Optimized for multimedia content analysis and video summarization."
        ],
        "SPO": {
            "subject": "Automated video analysis tool",
            "predicate": "analyzes video content using specialized AI models",
            "object": "for video summarization and multimedia content analysis"
        }
    },
    {
        "id": "Ask_AI",
        "input": ["prompt", "context"],
        "output": ["ai_response", "generated_text", "AI"],
        "tags": ["Chatbot", "AI Interaction", "Conversational AI"],
        "description": [
            "Interacts with a language model to generate answers or creative text.",
            "Facilitates dynamic dialogue and contextual summarization.",
            "Enhances user engagement with context-aware responses."
        ],
        "SPO": {
            "subject": "AI-powered chatbot",
            "predicate": "generates answers and creative text",
            "object": "for dynamic dialogue and context-aware responses"
        }
    },
    {
        "id": "Blog_Writer",
        "input": ["Content", "Target_Audience", "Tone", "Content_Length"],
        "output": ["blog", "blog_content", "blog_post"],
        "tags": ["Content Creation", "AI Writing", "Blog Writing"],
        "description": [
            "Generates comprehensive blog posts based on provided parameters.",
            "Creates engaging and targeted content for marketing and communication.",
            "Automates the writing process for consistent and creative outputs."
        ],
        "SPO": {
            "subject": "AI blog writer",
            "predicate": "generates comprehensive blog posts",
            "object": "for marketing, communication, and consistent content creation"
        }
    },
    {
        "id": "Get_Youtube_Transcript",
        "input": ["youtube_url", "video_url"],
        "output": ["transcript"],
        "tags": ["YouTube", "Transcription", "Video Transcript"],
        "description": [
            "Retrieves the transcript from a YouTube video URL.",
            "Efficiently extracts textual content for downstream analysis.",
            "Facilitates accurate video content processing and transcription tasks."
        ],
        "SPO": {
            "subject": "Automated YouTube transcript retriever",
            "predicate": "extracts transcripts from YouTube videos",
            "object": "for video content processing and transcription tasks"
        }
    },
    {
        "id": "summarize",
        "input": ["transcript", "content", "inputText"],
        "output": ["summary"],
        "tags": ["Text Summarization", "AI", "Summarization"],
        "description": [
            "Summarizes lengthy text, transcripts, or content using AI.",
            "Condenses information while retaining key points and context.",
            "Effective for producing concise summaries from extensive data."
        ],
        "SPO": {
            "subject": "AI summarization tool",
            "predicate": "summarizes text and transcripts",
            "object": "for condensing information while retaining key points"
        }
    },
    {
        "id": "generate_keywords",
        "input": ["text", "content"],
        "output": ["keywords"],
        "tags": ["Keyword Generation", "AI", "Keyword Extraction"],
        "description": [
            "Generates relevant keywords from a given text.",
            "Optimizes SEO and enhances content tagging for improved retrieval.",
            "Supports targeted marketing and efficient data indexing."
        ],
        "SPO": {
            "subject": "AI keyword generator",
            "predicate": "generates relevant keywords from text",
            "object": "for SEO optimization and efficient content tagging"
        }
    }
]

# Save workflow to database
def save_workflow(description: str, workflow_json: str):
    """Saves a workflow to the database with its embedding."""
    embedding = get_embeddings(description)
    if isinstance(embedding[0], list):
        embedding = embedding[0]
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="unicorn",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workflows (description, workflow, embedding) VALUES (%s, %s, %s)",
        (description, workflow_json, embedding_str)
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"\nWorkflow saved with description: {description}\n")

def get_embeddings(text: str) -> list:
    """Generates embeddings for a given text using a locally loaded model."""
    # Encode the input text to generate embeddings
    embeddings = model.encode([text])
    # Return the embeddings as a list
    return embeddings[0].tolist()

# Normalize embedding
def normalize_embedding(embedding):
    embedding = np.array(embedding)
    norm = np.linalg.norm(embedding)
    return (embedding / norm).tolist() if norm > 0 else embedding.tolist()

# Retrieve similar workflows from database
def retrieve_similar_workflow(query: str, top_k: int = 1, similarity_threshold: float = 0.8):
    """Retrieves similar workflows based on a query string."""
    query_embedding = get_embeddings(query)
    if isinstance(query_embedding[0], list):
        query_embedding = query_embedding[0]
    query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
    
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="unicorn",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT id, description, workflow, 1 - (embedding <-> %s) AS similarity
        FROM workflows
        ORDER BY similarity DESC
        LIMIT %s;
    """, (query_embedding_str, top_k))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return [(id, desc, wf, sim) for id, desc, wf, sim in results if sim >= similarity_threshold]

# Get embeddings from Hugging Face API
# def get_embeddings(text: str) -> list:
#     """Generates embeddings for a given text using Hugging Face API."""
#     response = client.feature_extraction(text, model="sentence-transformers/all-MiniLM-L6-v2")
#     return response.tolist()

# Generate and store node embeddings in batch
def generate_and_store_node_embeddings(nodes: List[Dict], update_embeddings: bool = True) -> None:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="unicorn",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    node_embeddings = []
    for node in nodes:
        input_text = ', '.join(node['input'])
        output_text = ', '.join(node['output'])
        tags_text = ', '.join(node['tags'])
        description_text = ', '.join(node['description'])
        spo_text = f"{node['SPO']['subject']} {node['SPO']['predicate']} {node['SPO']['object']}"
        
        # Generate overall node text
        node_text = f"{node['id']}: - input: {input_text} - output: {output_text} - tags: {tags_text} - description: {description_text} - SPO: {spo_text}"
        
        print(f"\nGenerating embedding for node: {node['id']}")
        print(f"Input: {input_text}")
        print(f"Output: {output_text}")
        print(f"Tags: {tags_text}")
        print(f"Description: {description_text}")
        print(f"SPO: {spo_text}\n")
        
        input_embedding = get_embeddings(input_text)
        output_embedding = get_embeddings(output_text)
        tags_embedding = get_embeddings(tags_text)
        description_embedding = get_embeddings(description_text)
        spo_embedding = get_embeddings(spo_text)
        overall_embedding = get_embeddings(node_text)
        
        # print(f"Input Embedding: {input_embedding}")
        # print(f"Output Embedding: {output_embedding}")
        # print(f"Tags Embedding: {tags_embedding}")
        # print(f"Description Embedding: {description_embedding}")
        # print(f"SPO Embedding: {spo_embedding}")
        # print(f"Overall Embedding: {overall_embedding}")

        if isinstance(input_embedding[0], list):
            input_embedding = input_embedding[0]
        if isinstance(output_embedding[0], list):
            output_embedding = output_embedding[0]
        if isinstance(tags_embedding[0], list):
            tags_embedding = tags_embedding[0]
        if isinstance(description_embedding[0], list):
            description_embedding = description_embedding[0]
        if isinstance(spo_embedding[0], list):
            spo_embedding = spo_embedding[0]
        if isinstance(overall_embedding[0], list):
            overall_embedding = overall_embedding[0]
        
        input_embedding = normalize_embedding(input_embedding)
        output_embedding = normalize_embedding(output_embedding)
        tags_embedding = normalize_embedding(tags_embedding)
        description_embedding = normalize_embedding(description_embedding)
        spo_embedding = normalize_embedding(spo_embedding)
        overall_embedding = normalize_embedding(overall_embedding)
        
        # Format embeddings for PostgreSQL using curly braces
        input_embedding_str = '[' + ','.join(map(str, input_embedding)) + ']'
        output_embedding_str = '[' + ','.join(map(str, output_embedding)) + ']'
        tags_embedding_str = '[' + ','.join(map(str, tags_embedding)) + ']'
        description_embedding_str = '[' + ','.join(map(str, description_embedding)) + ']'
        spo_embedding_str = '[' + ','.join(map(str, spo_embedding)) + ']'
        overall_embedding_str = '[' + ','.join(map(str, overall_embedding)) + ']'

        # print(f"\ninput_embedding_str: {input_embedding_str}\n")

        node_embeddings.append((
            node['id'],
            input_embedding_str,
            output_embedding_str,
            tags_embedding_str,
            description_embedding_str,
            spo_embedding_str,
            overall_embedding_str
        ))
    
    # print(f"\nnode_embeddings: {node_embeddings}\n")

    if update_embeddings:
        args_str = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)", (
            node_id,
            input_emb,
            output_emb,
            tags_emb,
            description_emb,
            spo_emb,
            overall_emb
        )).decode('utf-8') for node_id, input_emb, output_emb, tags_emb, description_emb, spo_emb, overall_emb in node_embeddings)
        cur.execute(
            "INSERT INTO node_embeddings (node_id, input_embedding, output_embedding, tags_embedding, description_embedding, spo_embedding, overall_embedding) VALUES " + args_str +
            " ON CONFLICT (node_id) DO UPDATE SET input_embedding = EXCLUDED.input_embedding, output_embedding = EXCLUDED.output_embedding, tags_embedding = EXCLUDED.tags_embedding, description_embedding = EXCLUDED.description_embedding, spo_embedding = EXCLUDED.spo_embedding, overall_embedding = EXCLUDED.overall_embedding;"
        )
    else:
        print("No embeddings stored becasue Flag is FALSE")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Node embeddings stored in batch.")

# Batch retrieval of similar nodes
def retrieve_similar_nodes_batch(subtask_texts: List, top_k: int = 5, similarity_threshold: float = 0.3) -> Dict[str, List[Tuple]]:
    """Retrieve similar nodes for each subtask based on normalized embeddings.
       Handles both dictionaries and strings for subtask_texts.
    """
    embeddings = []
    mapping_keys = []
    
    for text in subtask_texts:
        if isinstance(text, dict):
            subtask_text = text.get("description", "")
            key = text.get("description", subtask_text)
        else:
            subtask_text = text
            key = text
        mapping_keys.append(key)
    
        embedding = get_embeddings(subtask_text)
        if isinstance(embedding[0], list):
            embedding = embedding[0]
        embedding = normalize_embedding(embedding)
        embeddings.append(embedding)
    
    print(f"\n--- embeddings LEN (END): {len(embeddings)} ---\n")
    vector_embeddings = [f'[{",".join(map(str, emb))}]' for emb in embeddings]
    
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="unicorn",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM retrieve_similar_nodes_batch(
            %s::vector[],
            %s
        )
    """, (vector_embeddings, top_k))
    results = cur.fetchall()

    print(f"\n--- RESULTS Retrieved for similar nodes ---- : {results} ---\n")
    print(f"Number of subtasks: {len(subtask_texts)}")
    print(f"Query indices from results: {[row[0] for row in results]}")
    
    cur.close()
    conn.close()
    
    similar_nodes_by_query = {key: [] for key in mapping_keys}
    
    for query_index, node_id, similarity in results:
        if query_index > len(subtask_texts):
            print(f"Warning: Invalid query index {query_index} for {len(subtask_texts)} subtasks")
            continue
        try:
            key = mapping_keys[query_index - 1]  # Adjust for 1-based indexing from SQL
            node = next((n for n in AVAILABLE_NODES if n['id'] == node_id), None)
            similar_nodes_by_query[key].append((node, similarity))
        except IndexError:
            print(f"Invalid query_index: {query_index}, max index: {len(subtask_texts) - 1}")
            continue
    
    return similar_nodes_by_query

# Filter nodes by embedding batch
def filter_nodes_by_embedding_batch(blueprint_steps: List[Dict], nodes: List[Dict], top_k: int = 3) -> Dict[str, List[Dict]]:
    subtask_descriptions = [
        {
            "step": step["step"],
            "input": step["input"],
            "output": step["output"],
            "tags": step.get("tags", []),
            "description": step["description"],
            "SPO": step.get("SPO", ""),
            "description_embed": f"{step['step']}: - input: {step['input']} - output: {step['output']} - tags: {', '.join(step.get('tags', []))} - description: {step['description']} - SPO: {step.get('SPO', '')}"
        }
        for step in blueprint_steps
    ]
    
    similar_nodes_by_query = retrieve_similar_nodes_batch([step["description_embed"] for step in subtask_descriptions], top_k=top_k)

    for key, candidates in similar_nodes_by_query.items():
        print(f"\nCandidates for subtask description '{key}':")
        for candidate, similarity in candidates:
            # print(f"\nNode: {candidate['id']}, Input: {candidate['input']}, Output: {candidate['output']}, Similarity: {similarity:.4f}\n")
            print(f"\nNode: {candidate['id']}, Input: {candidate['input']}, Output: {candidate['output']}, SPO: {candidate['SPO']}, Similarity: {similarity:.4f}\n")

    filtered_nodes_map = {}
    missing_nodes_list = []
    
    for i, step in enumerate(blueprint_steps):
        subtask_description = subtask_descriptions[i]["description_embed"]
        filtered_nodes_with_similarity = similar_nodes_by_query.get(subtask_description, [])
        filtered_nodes = [node for node, _ in filtered_nodes_with_similarity[:top_k]]
        
        if not filtered_nodes:
            missing_nodes_list.append({
                "subtask": step['step'],
                "Function_Inputs": step['input'],
                "Function_Output": step['output'],
                "Function_Description": step['description'],
            })
            print(f"Warning: No nodes for '{step['step']}'")
            continue
        
        candidate_list = "\n".join([
            f"node: {node['id']}: input={node['input']}, output={node['output']}, tags={node['tags']}, description={node['description']}, SPO={node.get('SPO', '')}" 
            for node in filtered_nodes
        ])
        ai_prompt = f"""
        <Subtask_Details>
            Subtask Name: "{step['step']}"
            Input: {step['input']}
            Output: {step['output']}
            Tags: {step['tags']}
            Description: {step['description']}
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
        ai_response = Ask_AI(ai_prompt, context="Return valid JSON")
        print(f"ai_response filter_nodes_by_embedding_batch: {ai_response}")
        try:
            selected_nodes = []
            parsed_response = json.loads(ai_response)
            if isinstance(parsed_response, dict):
                if "MISSING_NODE" in parsed_response:
                    missing_nodes_list.append({
                        "subtask": step['step'],
                        "Function_Inputs": step['input'],
                        "Function_Output": step['output'],
                        "Function_Description": step['description'],
                    })
                    selected_nodes = []
                elif "SELECTED_NODE" in parsed_response:
                    selected_node_ids = parsed_response["SELECTED_NODE"]
                    selected_nodes = [node for node in filtered_nodes if node['id'] in selected_node_ids]
                else:
                    selected_nodes = []
            elif isinstance(parsed_response, list):
                selected_node_ids = parsed_response
                selected_nodes = [node for node in filtered_nodes if node['id'] in selected_node_ids]
            else:
                selected_nodes = []
        except Exception as e:
            print(f"AI response error or empty result for subtask '{step['step']}': {e}.")
            missing_nodes_list.append({
                "subtask": step['step'],
                "Function_Inputs": step['input'],
                "Function_Output": step['output'],
                "Function_Description": step['description'],
            })
            selected_nodes = []
            
        print(f"\n----Selected nodes for subtask '{step['step']}': {selected_nodes}\n----")
        filtered_nodes_map[step['step']] = validate_nodes(selected_nodes)
    
    print(f"\n--- filtered_nodes_map {filtered_nodes_map}---\n")
    if missing_nodes_list:
        print(f"\nMissing nodes detected for subtasks: {', '.join([m['subtask'] for m in missing_nodes_list])}")
        print(f"\nMissing nodes JSON: {json.dumps(missing_nodes_list, indent=4)}")
    
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

# prompt = f"""
# 1. Understand the overall intent and context by identifying key objectives and specific requirements. Remove any duplicate or redundant information.
# 2. Decompose the task into clear, meaningful subtasks that directly support the primary objective. Avoid splitting into trivial or overly granular steps (e.g., do not break a process into downloading, audio extraction, and transcript generation if one consolidated step suffices) and exclude non-essential actions unless explicitly required.
# """

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
    # Update to use subtask descriptions for embedding generation
    subtask_descriptions = [
        {
            "step": step["step"],
            "input": step["input"],
            "output": step["output"],
            "tags": step.get("tags", []),
            "description": step["description"],
            "SPO": step.get("SPO", ""),
            "description_embed": step["description_embed"]
        }
        for step in state["plan"]
    ]

    state["subtask_node_map"] = filter_nodes_by_embedding_batch(subtask_descriptions, state["available_nodes"])
    
    print(f"\n--- subtask_node_map (generate_plan_batch()) (FilteredNodes(subtask_descriptions)) {state['subtask_node_map']}---\n")
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

# final_workflow = generate_workflow('''I need a workflow that processes a YouTube video for marketing analysis. The workflow should:
# - Retrieve the video transcript from a given YouTube URL.
# - Summarize the transcript.
# - Analyze the summary to extract key insights.
#     - Use these insights to generate keywords via Ask_AI.
#     - Finally, write a blog post using Blog_Writer targeting a marketing audience.
# ''')

final_workflow = generate_workflow(UserTaskQuery)

print(f"Final Workflow:\n{final_workflow}")