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
from prompts.node_scehma import NODE_SCHEMA
from jinja2 import Environment, FileSystemLoader
from prompts.connection import get_connection
from prompts.available_nodes import AVAILABLE_NODES
from prompts.store_procedure import STORE_PROCEDURE_QUERIES
import sys
# Add the root directory (ai-workflow-research-py) to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(root_dir)
# from code_writer import Code_Agent_Node
env = Environment(loader=FileSystemLoader("prompts"))

# Load environment variables from .env file
load_dotenv()

def render_prompt(template_name: str, **kwargs) -> str:
    """
    Renders a prompt template using Jinja2.
    
    Template files (e.g., decompose_task.jinja2) should be placed in the prompts folder.
    """
    template = env.get_template(template_name)
    return template.render(**kwargs)

model_name = os.getenv("MODEL_NAME")

# Initialize clients using environment variables
client = InferenceClient(token=os.environ['HF_API_TOKEN'])

llm = ChatGroq(temperature=0, model=model_name)

import os
print("Current working directory:", os.getcwd())


# Database setup with batch stored procedures
def setup_database():
    """Sets up the PostgreSQL database with necessary tables and stored procedures."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Execute the stored procedure queries from external file
    cur.execute(STORE_PROCEDURE_QUERIES)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database setup completed with batch stored procedures.")
    

# Call setup
setup_database()


def process_missing_nodes(missing_nodes):

    """
    Process each missing node by passing it to Code_Agent_Node.
    """
    for node in missing_nodes:
        print(f"Processing node: {node['Function_Description']}")
        result = Code_Agent_Node(
            Function_Description=node["Function_Description"],
            Function_Inputs=node["Function_Inputs"],
            Function_Output=node["Function_Output"]
        )
        print(f"Result for {node['Function_Description']}: {result}\n")

# Save workflow to database
def save_workflow(description: str, workflow_json: str):
    """Saves a workflow to the database with its embedding."""
    embedding = get_embeddings(description)
    if isinstance(embedding[0], list):
        embedding = embedding[0]
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workflows_generator (description, workflow, embedding) VALUES (%s, %s, %s)",
        (description, workflow_json, embedding_str)
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"\nWorkflow saved with description: {description}\n")

# Retrieve similar workflows from database
def retrieve_similar_workflow(query: str, top_k: int = 1, similarity_threshold: float = 0.8):
    """Retrieves similar workflows based on a query string."""
    query_embedding = get_embeddings(query)
    if isinstance(query_embedding[0], list):
        query_embedding = query_embedding[0]
    query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, description, workflow, 1 - (embedding <-> %s) AS similarity
        FROM workflows_generator
        ORDER BY similarity DESC
        LIMIT %s;
    """, (query_embedding_str, top_k))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return [(id, desc, wf, sim) for id, desc, wf, sim in results if sim >= similarity_threshold]

# Batch retrieval of similar nodes
def retrieve_similar_nodes_batch(subtask_texts: List, top_k: int = 5, similarity_threshold: float = 0.3) -> Dict[str, List[Tuple]]:
    """Retrieve similar nodes for each subtask based on normalized embeddings.
       Handles both dictionaries and strings for subtask_texts.
    """
    embeddings = []
    # Also build a mapping list for keys (e.g., description if available)
    mapping_keys = []
    
    for text in subtask_texts:
        # If text is a dictionary, use its fields; otherwise treat it as a string
        print(f"\n--- texts: {text} ---\n")
        if isinstance(text, dict):
            subtask_text = text.get("description", "")
            # print(f"\n--- subtask_text: {subtask_text} ---\n")
            key = text.get("description", subtask_text)
            # print(f"\n--- key: {key} ---\n")
        else:
            subtask_text = text
            # print(f"\n--- subtask_text (ELSE): {subtask_text} ---\n")
            key = text
            # print(f"\n--- key (ELSE): {key} ---\n")
        mapping_keys.append(key)
    
        print(f"\n--- mapping_keys: {mapping_keys} ---\n")

        # Compute embedding and normalize it
        embedding = get_embeddings(subtask_text)
        if isinstance(embedding[0], list):
            embedding = embedding[0]
        embedding = normalize_embedding(embedding)
        embeddings.append(embedding)
    
    print(f"\n--- embeddings LEN (END): {len(embeddings)} ---\n")
    # Convert embeddings to PostgreSQL vector format (string formatted)
    vector_embeddings = [f'[{",".join(map(str, emb))}]' for emb in embeddings]
    
    # Connect to the database and execute the retrieval function
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM retrieve_similar_nodes_batch(
            %s::vector[],
            %s
        )
    """, (vector_embeddings, top_k))
    results = cur.fetchall()

    print(f"\n--- RESULTS ---- : {results} ---\n")
    print(f"Number of subtasks: {len(subtask_texts)}")
    print(f"Query indices from results: {[row[0] for row in results]}")
    
    cur.close()
    conn.close()
    
    # Build a dictionary with keys based on mapping_keys
    similar_nodes_by_query = {key: [] for key in mapping_keys}
    print(f"\n--- similar_nodes_by_query (Before): {similar_nodes_by_query} ---\n")

    for query_index, node_id, similarity in results:
        if query_index > len(subtask_texts):
            print(f"Warning: Invalid query index {query_index} for {len(subtask_texts)} subtasks")
            continue
        try:
            key = mapping_keys[query_index - 1]  # Adjust for 1-based indexing from SQL
            node = next((n for n in AVAILABLE_NODES if n['id'] == node_id), None)
            # if node and similarity >= similarity_threshold:
            similar_nodes_by_query[key].append((node, similarity))
        except IndexError:
            print(f"Invalid query_index: {query_index}, max index: {len(subtask_texts) - 1}")
            continue
    
    print(f"\nSimilar Nodes by Query (AFTER): {similar_nodes_by_query}\n")
    return similar_nodes_by_query


# Get embeddings from Hugging Face API #############################
def get_embeddings(text: str) -> list:
    """Generates embeddings for a given text using Hugging Face API."""
    response = client.feature_extraction(text, model="sentence-transformers/all-MiniLM-L6-v2")
    return response.tolist()

# Normalize embedding
def normalize_embedding(embedding):
    embedding = np.array(embedding)
    norm = np.linalg.norm(embedding)
    return (embedding / norm).tolist() if norm > 0 else embedding.tolist()

# Generate and store node embeddings in batch
def generate_and_store_node_embeddings(nodes: List[Dict]) -> None:
    """Generates embeddings for nodes and stores them in the database."""
    conn = get_connection()
    
    cur = conn.cursor()
    
    node_embeddings = []
    for node in nodes:
        node_text = f"{node['id']}: - input: {', '.join(node['input'])} - output: {', '.join(node['output'])} - tags: {', '.join(node['tags'])} - description: {node['description']} "
        print(f"\nGenerating embedding for node:generate_and_store_node_embeddings: {node_text}\n")
        embedding = get_embeddings(node_text)
        if isinstance(embedding[0], list):
            embedding = embedding[0]  # Flatten if nested
        embedding = normalize_embedding(embedding)  # Normalize to unit vector for cosine similarity
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        node_embeddings.append((node['id'], embedding_str))

    # Batch insert with ON CONFLICT for updates
    args_str = ','.join(cur.mogrify("(%s, %s)", (node_id, emb)).decode('utf-8') for node_id, emb in node_embeddings)
    cur.execute(
        "INSERT INTO node_embeddings (node_id, embedding) VALUES " + args_str +
        " ON CONFLICT (node_id) DO UPDATE SET embedding = EXCLUDED.embedding;"
    )
    
    conn.commit()
    cur.close()
    conn.close()
    print("Node embeddings stored in batch.")

# Filter nodes by embedding batch
def filter_nodes_by_embedding_batch(blueprint_steps: List[Dict], nodes: List[Dict], top_k: int = 5) -> Dict[str, List[Dict]]:
    """Filters nodes based on embeddings in batch."""
    subtask_descriptions = [
        {
            "step": step["step"],
            "input": step["input"],
            "output": step["output"],
            "tags": step.get("tags", []),
            "description": step["description"],
            "description_embed": step["description_embed"]
        }
        for step in blueprint_steps
    ]
    # print(f"\n_____ subtask_descriptions:filter_nodes_by_embedding_batch: {subtask_descriptions}______\n")

    # Retrieve top-K similar nodes for the batch of subtasks
    similar_nodes_by_query = retrieve_similar_nodes_batch([step["description_embed"] for step in subtask_descriptions], top_k=top_k)
    
    print(f"\n--- similar_nodes_by_query (Retrived): {similar_nodes_by_query} ---\n")

    filtered_nodes_map = {}
    missing_nodes_list = []

    for i, step in enumerate(blueprint_steps):
        print(f"+++++++++++++++++++++++++++++: {step['input']}")
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
            f"subtask={node['id']}: input={node['input']}, output={node['output']}, tags={node['tags']}, description={node['description']}" 
            for node in filtered_nodes
        ])
    
        
        ai_prompt = render_prompt("filter_nodes.jinja2",
                                    step=step['step'],
                                    input=step["input"],
                                    output=step['output'],
                                    tags=step['tags'] ,
                                    description=step['description'],
                                    candidate_list=candidate_list)
        
        print(f"ai_prompt_____________________________:{ai_prompt}")
        ai_response = Ask_AI(ai_prompt, context="Return valid JSON")
        try:
            parsed_response = json.loads(ai_response)
            if isinstance(parsed_response, dict):
                if "MISSING_NODE" in parsed_response:
                    # AI indicates missing node → mark this subtask as missing
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
            # selected_nodes = filtered_nodes[:top_k]
        print(f"\n----Selected nodes for subtask '{step['step']}': {selected_nodes}\n----")
        filtered_nodes_map[step['step']] = validate_nodes(selected_nodes)
    print(f"\n--- filtered_nodes_map {filtered_nodes_map}---\n")
    # If any subtasks are missing nodes, call the process_missing_nodes function with the missing nodes list.
    if missing_nodes_list:
        max_try=0
        while max_try<3:
            print(f"\nMissing nodes detected for subtasks: {', '.join([m['subtask'] for m in missing_nodes_list])}")
            print(f"\nMissing nodes JSON: {json.dumps(missing_nodes_list, indent=4)}")
            print(f"\npls call the code_writer to generate these nodes")

            print(f"+++++++++++++++++++++++{missing_nodes_list}")

            process_missing_nodes(missing_nodes_list)

            print(f"\nNodes have generated pls update the embedding to re check it")
            
            # After processing missing nodes, update the available nodes and embeddings
            # Recheck the similarity of nodes with the updated embeddings
            updated_nodes = AVAILABLE_NODES + [{
                "id": f"{i}",
                "input": node["Function_Inputs"],
                "output": node["Function_Output"],
                "tags": node["Tags"],
                "description": node["Function_Description"]
            } for i, node in enumerate(missing_nodes_list)]
            
            generate_and_store_node_embeddings(updated_nodes)
            
            # Re-retrieve similar nodes with updated embeddings
            similar_nodes_by_query = retrieve_similar_nodes_batch(subtask_descriptions, top_k=top_k)
            
            # Rebuild the filtered_nodes_map with updated similar nodes

            for i, step in enumerate(blueprint_steps):
                subtask_description = subtask_descriptions[i]
                filtered_nodes_with_similarity = similar_nodes_by_query.get(subtask_description, [])
                filtered_nodes = [node for node, _ in filtered_nodes_with_similarity[:top_k]]
                filtered_nodes_map[step['step']] = validate_nodes(filtered_nodes)

            if len(filtered_nodes_map) == len(blueprint_steps):
                break
            else:
                max_try=+1

        if max_try >= 3:
            return f"Unable to generate nodes"
            
    
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
    initial_workflow: List[Dict]
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
    state["initial_workflow"]= []
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
    """Decomposes the main task into subtasks."""
    prompt = render_prompt("decompose_task.jinja2", task=state["task"])
    print(f"decompose_task_____________________________:{prompt}")

    response = Ask_AI(prompt, context="Return valid JSON")
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

# Create initial subtask workflow (changed)
def create_initial_subtask_workflow(state: AgentState) -> AgentState:
    """Creates an initial workflow plan for subtasks."""
    # Use external prompt template "create_initial_subtask_workflow.jinja2"
    prompt = render_prompt("create_initial_subtask_workflow.jinja2", task=state["task"], subtasks=json.dumps(state["subtasks"]))
    print(f"create_initial_subtask_workflow_____________________________:{prompt}")

    response = Ask_AI(prompt, context="Return valid JSON")
    print(f"\nAI response for create_initial_subtask_workflow (blueprint): {response}\n")
    try:
        state["plan"] = json.loads(response)
        state['initial_workflow']=json.loads(response)

        print(f"initial_workflow_prior________________________________ : {state['initial_workflow']} ")
        # Update to include subtask descriptions for embedding generation
        for step in state["plan"]:
            step["description_embed"] = f"{step['step']}: - input: {step['input']} - output: {step['output'] } - tags: {', '.join(step.get('tags', []))} - description: {step['description']}"
        
        # print(f"\n--- state['plan'] ---------    {state['plan']}---\n")
    except Exception as e:
        print(f"Error parsing create_initial_subtask_workflow response: {e}")
        state["plan"] = [{"step": s, "input": [f"Input for {s}"], "output": [f"Output for {s}"],"tags": [f"tags for {s}"], "description": f"Description for {s}"} for s in state["subtasks"]]
    return state


def generate_workflow_from_plan(state: AgentState, plan: Optional[List[Dict]] = None, top_level: bool = True) -> Dict:
    """Convert the plan into a structured workflow with nodes and edges, excluding mappings."""
    if plan is None:
        plan = state["plan"]
    
    # Ensure special nodes are present in the plan
    if not any(step["node_id"] == "__start__" for step in plan):
        plan.insert(0, {"node_id": "__start__", "inputs": {}, "output": {}})
    if not any(step["node_id"] == "__end__" for step in plan):
        plan.append({"node_id": "__end__", "inputs": {}, "output": {}})
    
    # Build nodes list
    nodes_list = [create_callable_node(step, state) for step in plan if step.get("node_id") not in ["__start__", "__end__"]]
    start_node = {"id": "__start__", "type": "schema", "data": "__start__"}
    end_node = {"id": "__end__", "type": "schema", "data": "__end__"}
    nodes_list = nodes_list + [start_node, end_node]

    # Build edges list without mappings
    edges_list = []
    for i in range(len(plan) - 1):
        edge = {"source": plan[i]["node_id"], "target": plan[i + 1]["node_id"]}
        edges_list.append(edge)

    workflow_json = {
        "main":{
        "state": {"mainstate": "GraphState", "inputstate": None, "outputstate": None},
        "nodes": nodes_list,
        "edges": edges_list
    }
    }
    return workflow_json

# Generate plan batch (changed)
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
            "description_embed": step["description_embed"]
        }
        for step in state["plan"]
    ]
    filter_nodes_emb = filter_nodes_by_embedding_batch(subtask_descriptions, state["available_nodes"])

    if isinstance(filter_nodes_emb, str):
        print("Unable to generate nodes")  # This will be printed

        return ""
        
    else:
        state['subtask_node_map'] = filter_nodes_emb
    
    
    # print(f"\n--- subtask_node_map {state["subtask_node_map"]}---\n")
    plan = []
    for step in state["plan"]:
        nodes = state["subtask_node_map"].get(step["step"], [])
        if nodes:
            node_entry = {"node_id": nodes[0]["id"], "inputs": nodes[0]["input"], "output": nodes[0]["output"]}
            plan.append(node_entry)
        else:
            print(f"Warning: No nodes for '{step['step']}'")
    
    state["plan"] = plan
    print(f"\n------------Printing the Last Plan {plan}---------\n")
    return state

def execute_step(state: AgentState):
    """Executes the current step in the workflow plan."""
    current_step = state["current_step"]
    partial_plan = state["plan"][:state["current_step"] + 1]
    partial_workflow = generate_workflow_from_plan(state, plan=partial_plan)
    
    if not partial_workflow:
        return {"workflow_valid": False}
    
    state["current_step"] = current_step + 1
    state["workflow_valid"] = True
    state["final_workflow"] = partial_workflow
    return state

def finalize(state: AgentState):
    """Finalizes the workflow by mapping edges and saving the final workflow."""
    # Generate the final workflow
    final_workflow = state["final_workflow"]
    
    # Map the edges of the workflow
    state = map_workflow_edges(state)
    
    # Print and save the final workflow
    print("Final Workflow:")
    print(final_workflow)
    
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


def map_workflow_edges(state: AgentState) -> Dict:
    """
    Maps the edges of the workflow by analyzing the final workflow and adding input-output mappings.
    This function is called after the final workflow is generated to avoid multiple LLM calls.
    """
    final_workflow = state["final_workflow"]
    
    # Use external prompt template "map_workflow_edges.jinja2"
    prompt = render_prompt("map_workflow_edges.jinja2",
                           task=state['task'],
                           initial_workflow=state['initial_workflow'],
                           plan=state['plan'],
                           final_workflow=final_workflow)
    print(f"map_workflow_edges_____________________________:{prompt}")
    

    # Call the LLM to generate the mapping
    workflow_json = Ask_AI(prompt, context="Return valid JSON")
    print(f"\nAI response for WORKFLOW MAPPING: {workflow_json}\n")
    
    try:
        # Update the final workflow with the new edges
        mapped_workflow = json.loads(workflow_json)
        mapped_workflow['main']["state"]['mainstate'] = "GraphState"

        # Update the final workflow with the mapped workflow's state and edges
        final_workflow['main']['state'] = mapped_workflow['main']['state']
        final_workflow['main']["edges"] = mapped_workflow['main']["edges"]
        
        state["final_workflow"] = final_workflow
        return state 
    except Exception as e:
        print(f"AI response error or empty result for workflow mapping: {e}.")
    
    return state

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
        "initial_workflow":[],
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

# # Example usage
# final_workflow = generate_workflow('''I need a workflow that processes a YouTube video for marketing analysis. The workflow should:
# - Retrieve the YouTube transcript from the YouTube_URL.
# - Summarize the transcript via Ask_AI.''')

# print(f"Final Workflow:\n{final_workflow}")