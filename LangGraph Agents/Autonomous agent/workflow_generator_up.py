from typing import TypedDict, List, Dict, Literal, Optional
import json
import os
from langgraph.graph import StateGraph, END, START
from langchain_groq import ChatGroq
from jsonschema import validate, ValidationError
from huggingface_hub import InferenceClient
import numpy as np
import torch
from sentence_transformers import util  # Added this line
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Verify keys are loaded (optional debugging)
print("GROQ_API_KEY:", os.environ.get('GROQ_API_KEY', 'Not found'))
print("HF_API_TOKEN:", os.environ.get('HF_API_TOKEN', 'Not found'))

# Initialize clients AFTER loading environment variables
client = InferenceClient(token=os.environ['HF_API_TOKEN'])  # Hugging Face API for embeddings
llm = ChatGroq(temperature=0, model="llama-3.3-70b-versatile")  # Groq API for LLM

# Define the JSON schema for the nodes
NODE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "inputs": {
                "type": "object",
                "additionalProperties": {"type": "string"}
            },
            "output": {
                "type": "object",
                "additionalProperties": {"type": "string"}
            }
        },
        "required": ["id", "inputs", "output"]
    }
}

# Update with all Node JSON:
AVAILABLE_NODES = [
    {
        "id": "userRegistration",
        "inputs": {},
        "output": {}
    },
    {
        "id": "collectUserInfo",
        "inputs": { "formData": "" },
        "output": { "userData": "" }
    },
    {
        "id": "verifyEmail",
        "inputs": { "userEmail": "" },
        "output": { "verificationStatus": "" }
    },
    {
        "id": "paymentSetup",
        "inputs": { "subscriptionChoice": "" },
        "output": { "paymentStatus": "" }
    },
    {
        "id": "sendWelcomeEmail",
        "inputs": { "email": "" },
        "output": { "emailSent": "" }
    },
    {
        "id": "analyze_image",
        "inputs": {"image_file": "", "prompt": ""},
        "output": {"image_analysis": ""}
    },
    {
        "id": "website_scraper",
        "inputs": {"website_url": ""},
        "output": {"webiste_content": ""}
    },
    {
        "id": "analyze_video",
        "inputs": {"video_file": "", "prompt": "", "video_model": ""},
        "output": {"video_analysis": ""}
    },
    {
        "id": "Ask_AI",
        "inputs": {"prompt": "", "context": ""},
        "output": {"ai_response": ""}
    },
    {
        "id": "Blog_Writer",
        "inputs": {"Content": "", "Target_Audience": "", "Tone": "", "Content_Length": ""},
        "output": {"blog": ""}
    },
    {
        "id": "Get_Youtube_Transcript",
        "inputs": {"youtube_url": ""},
        "output": {"transcript": ""}
    },
    {
        "id": "analyze_summary",
        "inputs": {"summary": ""},
        "output": {"insights": ""}
    },
    {
        "id": "summarize",
        "inputs": {"inputText": ""},
        "output": {"summary": ""}
    },
    {
    "id": "order_received",
    "inputs": { "order_details": "", "customer_id": "" },
    "output": { "order_data": "" }
    },
    {
        "id": "validate_order",
        "inputs": { "order_data": "" },
        "output": { "is_valid": "" }
    },
    {
        "id": "payment_processing",
        "inputs": { "order_data": "", "payment_info": "" },
        "output": { "payment_status": "" }
    },
    {
        "id": "inventory_check",
        "inputs": { "order_data": "" },
        "output": { "stock_available": "" }
    },
    {
        "id": "inventory_update",
        "inputs": { "order_data": "" },
        "output": { "updated_inventory": "" }
    },
    {
        "id": "order_confirmation",
        "inputs": { "order_data": "", "payment_status": "" },
        "output": { "confirmation": "" }
    },
    {
        "id": "shipping_label_generator",
        "inputs": { "order_data": "", "shipping_address": "" },
        "output": { "label": "" }
    },
    {
        "id": "package_dispatch",
        "inputs": { "order_data": "", "label": "" },
        "output": { "dispatch_status": "" }
    },
    {
        "id": "email_notification",
        "inputs": { "order_data": "", "dispatch_status": "" },
        "output": { "notification_status": "" }
    },
    {
        "id": "translate_text",
        "inputs": { "text": "", "target_language": "English" },
        "output": { "translated_text": "" }
    },
    {
        "id": "customer_feedback_collection",
        "inputs": { "customer_id": "", "feedback": "" },
        "output": { "collected_feedback": "" }
    },
    {
        "id": "sentiment_analysis",
        "inputs": { "text": "" },
        "output": { "sentiment_score": "", "sentiment_label": "" }
    },
    {
        "id": "keyword_extractor",
        "inputs": { "text": "", "num_keywords": 5 },
        "output": { "keywords": "" }
    },
    {
        "id": "social_media_generator",
        "inputs": { "content": "", "platform": "Twitter", "tone": "Professional" },
        "output": { "social_media_post": "" }
    },
    {
        "id": "data_visualizer",
        "inputs": { "dataset": "", "chart_type": "bar" },
        "output": { "visualization": "" }
    },
    {
        "id": "text_to_speech",
        "inputs": { "text": "", "language": "en-US" },
        "output": { "audio_file": "" }
    },
    {
        "id": "pdf_to_text",
        "inputs": { "pdf_file": "" },
        "output": { "text": "" }
    },
    {
        "id": "email_sender",
        "inputs": { "recipient": "", "subject": "", "body": "" },
        "output": { "status": "" }
    },
    {
    "id": "prePublishing",
    "inputs": {
      "contentConcept": "description of the content idea",
      "strategyBrief": "overview of the pre-publishing strategy"
    },
    "output": {
      "prePublishPlan": "detailed plan including keyword research, content creation, and design assets"
    }
    },
    {
        "id": "publishing",
        "inputs": {
        "contentPackage": "final content and visual assets"
        },
        "output": {
        "publishingStatus": "confirmation of content publication and website update"
        }
    },
    {
        "id": "promotion",
        "inputs": {
        "publishedContent": "details of the live content"
        },
        "output": {
        "promotionResults": "metrics from social media, email, outreach, and paid campaigns"
        }
    },
    {
        "id": "monitoringAnalysis",
        "inputs": {
        "promotionResults": "collected engagement and analytics data"
        },
        "output": {
        "performanceReport": "comprehensive performance analysis and recommendations"
        }
    },
    {
        "id": "keywordResearch",
        "inputs": {
        "topic": "niche or subject area for content",
        "competitorURLs": "list of competitor website URLs"
        },
        "output": {
        "keywords": "list of target keywords",
        "analysisReport": "report on keyword difficulty, search volume, and competitor rankings"
        }
    },
    {
        "id": "contentCreation",
        "inputs": {
        "keywordData": "results from keywordResearch"
        },
        "output": {
        "contentDraft": "compiled content draft ready for further processing"
        }
    },
    {
        "id": "visualAssets",
        "inputs": {
        "contentDraft": "draft content for visual reference"
        },
        "output": {
        "assetsPackage": "collection of images, infographics, and videos"
        }
    },
    {
        "id": "draftContent",
        "inputs": {
        "contentOutline": "structured outline of the content"
        },
        "output": {
        "draftText": "initial version of the content draft"
        }
    },
    {
        "id": "editProofread",
        "inputs": {
        "draftText": "raw content draft"
        },
        "output": {
        "editedText": "proofread and edited content"
        }
    },
    {
        "id": "optimizeContent",
        "inputs": {
        "editedText": "edited content draft",
        "targetKeywords": "list of target keywords from keywordResearch"
        },
        "output": {
        "optimizedContent": "final SEO-optimized content"
        }
    },
    {
        "id": "schedulePublish",
        "inputs": {
        "contentPackage": "combined optimized content and visual assets"
        },
        "output": {
        "publishSchedule": "scheduled publication date/time and confirmation"
        }
    },
    {
        "id": "updateWebsite",
        "inputs": {
        "publishedContent": "content that has been scheduled/published"
        },
        "output": {
        "websiteUpdateStatus": "confirmation of updated website sections",
        "sitemapStatus": "confirmation of XML sitemap update"
        }
    },
    {
        "id": "socialMedia",
        "inputs": {
        "content": "details of the published content"
        },
        "output": {
        "socialEngagementMetrics": "engagement data from social media platforms"
        }
    },
    {
        "id": "emailMarketing",
        "inputs": {
        "subscriberList": "segmented email subscribers",
        "emailContent": "content tailored for the email campaign"
        },
        "output": {
        "emailCampaignMetrics": "open rates, click-through rates, and other email performance data"
        }
    },
    {
        "id": "outreach",
        "inputs": {
        "influencerDatabase": "list of potential influencers and industry contacts"
        },
        "output": {
        "outreachResults": "responses and engagement metrics from outreach efforts"
        }
    },
    {
        "id": "paidPromotion",
        "inputs": {
        "adBudget": "allocated budget for paid promotion",
        "adContent": "content optimized for paid advertising"
        },
        "output": {
        "adPerformance": "metrics on ad impressions, clicks, and conversions"
        }
    },
    {
        "id": "trackMetrics",
        "inputs": {
        "analyticsData": "data from Google Analytics, social media, and email platforms"
        },
        "output": {
        "performanceData": "aggregated performance metrics across channels"
        }
    },
    {
        "id": "analyzeResults",
        "inputs": {
        "performanceData": "aggregated performance metrics"
        },
        "output": {
        "strategyRecommendations": "detailed recommendations for content and promotion improvements"
        }
    }
]

# Example for plan step (reference only)
example = [
    {
        "node_id": "Get_Youtube_Transcript",
        "inputs": {
            "youtube_url": "https://www.youtube.com/watch?v=2mSNIX-l_Zc"
        },
        "output": {"transcript": ""}
    },
    {
        "node_id": "summarize",
        "inputs": {
            "inputText": "Get_Youtube_Transcript.transcript"
        },
        "output": {"summary": ""},
        "conditional_edge": {
            "conditional": True,
            "condition_type": "dict",
            "function": "validate_summary"
        }
    },
    {
        "node_id": "Blog_Writer",
        "inputs": {
            "Content": "summarize.summary",
            "Target_Audience": "General",
            "Tone": "Informative",
            "Content_Length": "Medium"
        },
        "output": {"blog": ""},
        "conditional_edge": {
            "conditional": True,
            "condition_type": "list",
            "function": "validate_blog_content"
        },
        "sub_plan": [
            {
                "node_id": "Ask_AI",
                "inputs": {
                    "prompt": "Generate a catchy title for the blog post",
                    "context": "Based on the summarized content"
                },
                "output": {"ai_response": ""}
            },
            {
                "node_id": "analyze_image",
                "inputs": {
                    "image_file": "path/to/image.jpg",
                    "prompt": "Analyze blog header image"
                },
                "output": {"image_analysis": ""},
                "conditional_edge": {
                    "conditional": True,
                    "condition_type": "dict",
                    "function": "check_image_quality"
                }
            }
        ]
    }
]
    # Decomposes the main task into subtasks and suggests initial nodes
    # Uses AI to break down the task and map subtasks to relevant nodes
# Global get_embeddings function for reusability across the workflow
# Takes a text string and returns its embedding as a list using the Hugging Face API

# Placeholder for NODE_SCHEMA (define this based on your requirements)
NODE_SCHEMA = {"type": "array", "items": {"type": "object"}}


# Global get_embeddings function
def get_embeddings(text: str) -> list:
    """Generate embeddings for a text string using Hugging Face's sentence-transformers."""
    # Replace 'client' with your actual client implementation
    response = client.feature_extraction(text, model="BAAI/bge-m3")
    return response.tolist()

# Function to interact with AI
def Ask_AI(prompt: str, context: str = "Follow all instructions completely") -> str:
    """Interact with the AI model, ensuring JSON-only responses when specified."""
    if not prompt:
        return "Error: 'prompt' is a required input."
    messages = [("system", prompt), ("human", f"<context>\n{context}\n</context>")]
    response = llm.invoke(messages)  # Replace 'llm' with your actual model instance
    raw_response = response.content if response else "Error: Failed to generate response."
    # Extract JSON if context demands it
    if "Return valid JSON" in context:
        import re
        json_match = re.search(r'\{.*\}|\[.*\]', raw_response, re.DOTALL)
        return json_match.group(0) if json_match else f"Error: Invalid JSON response - {raw_response}"
    return raw_response

# Validate nodes against schema
def validate_nodes(nodes: List[Dict]) -> List[Dict]:
    """Validate node structure against a predefined schema."""
    try:
        validate(instance=nodes, schema=NODE_SCHEMA)
        return nodes
    except ValidationError as e:
        print(f"Validation error: {e}")
        return AVAILABLE_NODES

# AgentState definition
class AgentState(TypedDict):
    task: str
    allowed_nodes: List[str]
    available_nodes: List[Dict]
    subtasks: List[str]
    subtask_sequence: List[str]
    subtask_node_map: Dict[str, List[Dict]]
    plan: List[Dict]  # This holds the blueprint
    context: str
    current_step: int
    workflow_valid: Optional[bool]
    final_workflow: Optional[Dict]
    evaluation: dict
    replan_attempts: int

# Initialize state
def initialize_state(state: AgentState):
    """Set up the initial AgentState with default values."""
    state["available_nodes"] = AVAILABLE_NODES
    state["subtasks"] = []
    state["subtask_sequence"] = []
    state["subtask_node_map"] = {}
    state["plan"] = []  # Will store the blueprint
    state["context"] = ""
    state["workflow_valid"] = None
    state["current_step"] = 0
    state["evaluation"] = {}
    state["replan_attempts"] = 0
    state["final_workflow"] = {}
    return state

# Decompose task into subtasks
def decompose_task(state: AgentState):
    """Break the main task into subtasks and their sequence using AI, ensuring alignment with task details."""
    prompt = f"""
Given the task: "{state['task']}"
Break it into distinct subtasks and specify their sequence, fully reflecting the task description.
Do NOT include __start__ or __end__ in the subtasks or sequence.
Return ONLY a JSON object with:
- "subtasks": list of subtask names matching the full task (including sub-workflow steps)
- "sequence": list showing execution order
    Example for "Process YouTube video for marketing analysis with sub-workflow":
    {{
        "subtasks": [
            "Retrieve video transcript",
            "Summarize transcript",
            "Analyze summary to extract key insights",
            "Generate keywords via Ask_AI",
            "Write blog post using Blog_Writer"
        ],
        "sequence": [
            "Retrieve video transcript",
            "Summarize transcript",
            "Analyze summary to extract key insights",
            "Generate keywords via Ask_AI",
            "Write blog post using Blog_Writer"
        ]
    }}
    NO additional text or explanations.
    """
    response = Ask_AI(prompt, context="Return valid JSON")
    print(f"AI response for decompose_task: {response}")  # Debug output
    try:
        result = json.loads(response)
        state["subtasks"] = result["subtasks"]
        state["subtask_sequence"] = result["sequence"]
    except Exception as e:
        print(f"Error parsing decompose_task response: {e}")
        # Fallback with full task breakdown
        state["subtasks"] = [
            "Retrieve video transcript",
            "Summarize transcript",
            "Analyze summary to extract key insights",
            "Generate keywords via Ask_AI",
            "Write blog post using Blog_Writer"
        ]
        state["subtask_sequence"] = state["subtasks"]
    return state

# Create initial subtask workflow (blueprint)
def create_initial_subtask_workflow(state: AgentState) -> AgentState:
    """
    Generate a blueprint with detailed requirements for each subtask, including optional sub-workflows and conditional edges.
    
    This enhanced version allows the AI to dynamically decide if a subtask requires a sub-workflow or conditional logic,
    making the blueprint more flexible and reducing the need for hardcoded rules elsewhere in the workflow.
    
    Args:
        state (AgentState): The current state containing 'task' and 'subtasks'.
    
    Returns:
        AgentState: The updated state with the blueprint stored in state["plan"].
    """
    # Updated prompt instructs the AI to include optional sub-workflow and conditional edge details
    prompt = f"""
    Given the task: "{state['task']}"
    And the subtasks: {json.dumps(state['subtasks'])}
    For each subtask, define:
    - Input requirements: what data is needed (as a list)
    - Output expectations: what result should be produced (as a list)
    - Business objective: why this subtask is important
    - Sub-workflow: if this subtask requires a sub-workflow, provide a list of nodes with their "node_id", "inputs", and "output"
    - Conditional edge: if this subtask has a conditional edge, provide details with "conditional", "condition_type", and "function"
    Return ONLY a JSON list of dictionaries with keys: "step", "input_requirements", "output_expectations", "business_objective", 
    and optionally "sub_workflow" and "conditional_edge"
    NO additional text or explanations.
    """
    # Send the prompt to the AI and get its response
    response = Ask_AI(prompt, context="Return a valid JSON list")
    print(f"AI response for blueprint: {response}")  # Debug output to inspect the AI’s response
    
    try:
        # Parse the AI’s response into a JSON object
        initial_blueprint = json.loads(response)
        # Store the blueprint in the state under "plan"
        state["plan"] = initial_blueprint
    except Exception as e:
        # If parsing fails, print the error and use a fallback blueprint
        print(f"Error creating blueprint: {e}")
        # Fallback: generate a basic blueprint (no sub-workflows or conditional edges)
        state["plan"] = [
            {
                "step": subtask,  # The subtask name
                "input_requirements": [f"Data required for '{subtask}'"],  # Generic input placeholder
                "output_expectations": [f"Expected output from '{subtask}'"],  # Generic output placeholder
                "business_objective": f"Purpose of '{subtask}'"  # Generic objective placeholder
            } for subtask in state["subtasks"]  # Iterate over all subtasks
        ]
    # Return the updated state with the blueprint
    return state

# Filter nodes by embedding using blueprint details
def filter_nodes_by_embedding(blueprint_step: Dict, nodes: List[Dict], top_k: int = 1) -> List[Dict]:
    """Filter nodes using blueprint details, ensuring one unique best match per subtask."""
    # Construct a detailed subtask description from the blueprint
    subtask_description = (
        f"{blueprint_step['step']} - "
        f"Inputs: {blueprint_step['input_requirements']} "
        f"Outputs: {blueprint_step['output_expectations']} "
        f"Objective: {blueprint_step['business_objective']}"
    )
    node_descriptions = [
        f"{node['id']} - Inputs: {list(node['inputs'].keys())} Outputs: {list(node['output'].keys())}"
        for node in nodes
    ]
    
    # Generate embeddings
    subtask_embedding = torch.tensor([get_embeddings(subtask_description)])
    node_embeddings = torch.tensor([get_embeddings(desc) for desc in node_descriptions])
    similarities = util.pytorch_cos_sim(subtask_embedding, node_embeddings)[0].numpy()
    
    # Filter top candidates
    top_indices = np.argsort(similarities)[-top_k*2:][::-1]
    filtered_nodes = [nodes[i] for i in top_indices if similarities[i] > 0.5]
    if not filtered_nodes:
        filtered_nodes = [nodes[i] for i in top_indices[:top_k]]
    
    # Prepare AI prompt with blueprint details
    candidate_list = "\n".join([
        f"- {node['id']}: Inputs={list(node['inputs'].keys())}, Outputs={list(node['output'].keys())}"
        for node in filtered_nodes
    ])
    ai_prompt = f"""
    Given the subtask: "{blueprint_step['step']}"
    Input requirements: {blueprint_step['input_requirements']}
    Output expectations: {blueprint_step['output_expectations']}
    Business objective: {blueprint_step['business_objective']}
    Candidate nodes:
    {candidate_list}
    Select exactly {top_k} unique node(s) that best match the subtask's requirements based on functionality.
    Return ONLY a JSON list of node IDs, e.g., ["node1"]
    NO additional text or duplicates.
    """
    ai_response = Ask_AI(ai_prompt, context="Return valid JSON")
    print(f"AI response for node selection: {ai_response}")  # Debug output
    try:
        selected_node_ids = list(set(json.loads(ai_response)))  # Deduplicate and limit to top_k
        filtered_nodes = [node for node in filtered_nodes if node['id'] in selected_node_ids][:top_k]
    except Exception as e:
        print(f"Error parsing node selection: {e}")
        filtered_nodes = filtered_nodes[:top_k]
    
    return validate_nodes(filtered_nodes) if filtered_nodes else nodes[:top_k]

# Generate plan using blueprint
def generate_plan(state: AgentState):
    """Generate the workflow plan using blueprint steps, ensuring alignment and dynamic sub-workflow inclusion."""
    MAX_REPLAN_ATTEMPTS = 3
    state["replan_attempts"] = state.get("replan_attempts", 0)

    # Create the blueprint and ensure subtask_sequence matches
    state = create_initial_subtask_workflow(state)
    state["plan"] = [step for step in state["plan"] if step["step"] not in ["__start__", "__end__"]]
    state["subtask_sequence"] = [step["step"] for step in state["plan"]]  # Sync subtask_sequence with blueprint

    # Filter nodes using blueprint details
    nodes_for_filtering = state["available_nodes"]

    for blueprint_step in state["plan"]:
        subtask = blueprint_step["step"]
        state["subtask_node_map"][subtask] = filter_nodes_by_embedding(blueprint_step, nodes_for_filtering, top_k=1)

    # Build the plan dynamically using the blueprint
    plan = []
    for blueprint_step in state["plan"]:
        subtask = blueprint_step["step"]
        nodes = state["subtask_node_map"].get(subtask, [])
        if nodes:
            node_entry = {
                "node_id": nodes[0]["id"],
                "inputs": nodes[0]["inputs"],
                "output": nodes[0]["output"]
            }
            # Dynamically add sub-plan if specified in the blueprint
            if "sub_workflow" in blueprint_step:
                node_entry["sub_plan"] = blueprint_step["sub_workflow"]
            plan.append(node_entry)
        else:
            print(f"Warning: No nodes for '{subtask}'")

    # Add __start__ and __end__ only once
    plan.insert(0, {"node_id": "__start__", "inputs": {}, "output": {}})
    plan.append({"node_id": "__end__", "inputs": {}, "output": {}})
    
    state["plan"] = plan
    return state

# Execute step
def execute_step(state: AgentState):
    """Execute the plan step-by-step, building partial workflows."""
    partial_plan = state["plan"][:state["current_step"] + 1]
    partial_workflow = generate_workflow_from_plan(state, plan=partial_plan)
    print(f"Partial Workflow at step {state['current_step'] + 1}:\n{json.dumps(partial_workflow, indent=4)}")
    state["current_step"] += 1
    state["workflow_valid"] = True
    state["final_workflow"] = partial_workflow
    return state

# Finalize workflow
def finalize(state: AgentState):
    """Finalize and output the complete workflow."""
    final_workflow = generate_workflow_from_plan(state)
    print(f"Final Workflow:\n{json.dumps(final_workflow, indent=4)}")
    state["final_workflow"] = final_workflow
    return state

# Helper to generate workflow from plan
def generate_workflow_from_plan(state: AgentState, plan: Optional[List[Dict]] = None, top_level: bool = True) -> Dict:
    """Convert the plan into a structured workflow with nodes and edges, including sub-workflows."""
    if plan is None:
        plan = state["plan"]
    if not any(step["node_id"] == "__start__" for step in plan):
        plan.insert(0, {"node_id": "__start__", "inputs": {}, "output": {}})
    if not any(step["node_id"] == "__end__" for step in plan):
        plan.append({"node_id": "__end__", "inputs": {}, "output": {}})
    
    compiled_steps = [step for step in plan if step.get("node_id") not in ["__start__", "__end__"] and "sub_plan" in step]
    callable_steps = [step for step in plan if step.get("node_id") not in ["__start__", "__end__"] and "sub_plan" not in step]
    compiled_nodes = [create_compiled_node(step, state) for step in compiled_steps]
    callable_nodes = [create_callable_node(step, state) for step in callable_steps]
    start_node = {"id": "__start__", "type": "schema", "data": "__start__"}
    end_node = {"id": "__end__", "type": "schema", "data": "__end__"}
    nodes_list = compiled_nodes + callable_nodes + [start_node, end_node]
    
    edges_list = []
    for i in range(len(plan) - 1):
        edge = {"source": plan[i]["node_id"], "target": plan[i + 1]["node_id"]}
        if "conditional_edge" in plan[i + 1]:
            cond = plan[i + 1]["conditional_edge"]
            edge.update({"conditional": cond["conditional"], "condition_type": cond["condition_type"], "function": cond["function"]})
        edges_list.append(edge)
    
    workflow_json = {"state": {"mainstate": None, "inputstate": None, "outputstate": None}, "nodes": nodes_list, "edges": edges_list}
    sub_workflows = {step["node_id"]: generate_workflow_from_plan(state, step["sub_plan"], False) for step in plan if "sub_plan" in step}
    final_workflow = {"main": workflow_json} if top_level else workflow_json
    final_workflow.update(sub_workflows)
    return final_workflow

def create_compiled_node(step: Dict, state: AgentState) -> Dict:
    """Create a compiled node for steps with sub-plans."""
    return {
        "id": step["node_id"],
        "type": "runnable",
        "data": {"id": ["langgraph", "graph", "state", "CompiledStateGraph"], "name": step["node_id"]},
        "inputs": step.get("inputs", {}),
        "output": step.get("output", {})
    }

def create_callable_node(step: Dict, state: AgentState) -> Dict:
    """Create a callable node for standalone steps."""
    return {
        "id": step["node_id"],
        "type": "runnable",
        "data": {"id": ["langgraph", "utils", "runnable", "RunnableCallable"], "name": step["node_id"]},
        "inputs": step.get("inputs", {}),
        "output": step.get("output", {})
    }

# Create planning workflow
def create_planning_workflow():
    """Define the StateGraph for the planning process."""
    workflow = StateGraph(AgentState)
    workflow.add_node("init", initialize_state)
    workflow.add_node("decompose", decompose_task)
    workflow.add_node("planning", generate_plan)
    workflow.add_node("execute", execute_step)
    workflow.add_node("finalize", finalize)
    
    workflow.add_edge("init", "decompose")
    workflow.add_edge("decompose", "planning")
    workflow.add_edge("planning", "execute")
    
    def decide_next_step(state: AgentState) -> Literal["planning", "execute", "finalize"]:
        if state.get("workflow_valid") is False:
            return "planning"
        elif state["plan"] and state["current_step"] >= len(state["plan"]):
            return "finalize"
        return "execute"
    
    workflow.add_conditional_edges("execute", decide_next_step, {"planning": "planning", "execute": "execute", "finalize": "finalize"})
    workflow.set_entry_point("init")
    return workflow.compile()

# Generate workflow
def generate_workflow(user_task, allowed_nodes: Optional[List[str]] = None):
    """Generate the final workflow for a given task."""
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
    planning_workflow = create_planning_workflow()
    final_state = planning_workflow.invoke(initial_state, {"recursion_limit": 100})
    return json.dumps(final_state.get('final_workflow', {}), indent=4)

# Example usage
final_workflow = generate_workflow('''I need a workflow that processes a YouTube video for marketing analysis. The workflow should:
- Retrieve the video transcript from a given YouTube URL.
- Summarize the transcript.
- Analyze the summary to extract key insights.
create sub workflow of this node included these 2 nodes below:
    - Use these insights to generate keywords via Ask_AI.
    - Finally, write a blog post using Blog_Writer targeting a marketing audience.
Ensure the workflow follows the UPDATED_JSON_WORKFLOW_SCHEMA with __start__ and __end__ nodes correctly placed.''')
print(f"Final Workflow:\n{final_workflow}")

if __name__ == "__main__":
    text = "This is a test sentence for embeddings."
    embedding = get_embeddings(text)
    print(f"Embedding length: {len(embedding)}")
    print(f"First few values: {embedding[:5]}")
    ai_response = Ask_AI("Hello, how are you?")
    print(f"AI response: {ai_response}")