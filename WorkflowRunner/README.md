0. It takes the Json and create the LangGraph Workflow

1. File to Store JSON Configurations
File Name: graph_configs.json

Purpose: Store JSON configurations for different workflows (e.g., self_Rag_Agent, YouTube Transcript Summarizer, etc.).

Example:

json
Copy
{
  "self_Rag_Agent": {
    "nodes": [...],
    "edges": [...]
  },
  "YouTube_Summarizer": {
    "nodes": [...],
    "edges": [...]
  }
}
2. File to Store Functions
File Name: workflow_functions.py

Purpose: Define all the functions used in the workflows (e.g., retrieve, grade_documents, generate, etc.).

Example:

python
Copy
def retrieve(state):
    # Function logic
    return state

def grade_documents(state):
    # Function logic
    return state
3. File to Store Chat Templates
File Name: chat_templates.py

Purpose: Store predefined chat templates or prompts for functions like Ask_AI, summarize, etc.

Example:

python
Copy
ASK_AI_PROMPT = """
Use the provided blog content to repurpose the blog. Make sure to follow the instructions closely.
Do not plagiarize or directly take content from the provided draft. The goal is to turn the existing blog post into fresh content.
Output just the repurposed content without any introductory or explanatory text. Output in markdown without any markdown backticks!
Instructions:
Reason of Repurposing: Email Campaign Content
Target Audience: CEO/Founders
Tone & Style: Formal
Content Length: Medium (e.g., 300-500 words)
"""
4. File to Configure LLMs
File Name: llm_config.py

Purpose: Configure and initialize different LLMs (e.g., Groq, GPT, Llama).

Example:

python
Copy
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

def get_llm(model_name="groq"):
    if model_name == "groq":
        return ChatGroq(model="mixtral-8x7b-32768")
    elif model_name == "gpt":
        return ChatOpenAI(model="gpt-4")
    elif model_name == "llama":
        return ChatOpenAI(model="llama-2")
5. File to Store StateGraph Definitions
File Name: state_graphs.py

Purpose: Define StateGraph classes for different workflows.

Example:

python
Copy
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    question: str
    generation: str
    documents: list
6. File for Main Code to Convert JSON to LangGraph
File Name: json_to_langgraph.py

Purpose: Main logic to convert JSON configurations into executable LangGraph workflows.

Example:

python
Copy
from langgraph.graph import StateGraph, END, START
from .workflow_functions import function_registry
from .state_graphs import GraphState

def build_graph_from_json(json_config):
    workflow = StateGraph(GraphState)
    # Add nodes and edges based on JSON
    return workflow.compile()
7. File to Store Function Registrations
File Name: function_registry.py

Purpose: Register all functions in a central registry for easy access.

Example:

python
Copy
from .workflow_functions import retrieve, grade_documents, generate

function_registry = {
    "retrieve": retrieve,
    "grade_documents": grade_documents,
    "generate": generate,
}
8. File for Utility Functions
File Name: utils.py

Purpose: Store helper functions like extract_runnable_node_list, group_by_source_and_function, etc.

**Example:

python
Copy
def extract_runnable_node_list(input_json):
    return [node for node in input_json["nodes"] if node["type"] == "runnable"]
9. File for Running the Workflow
File Name: run_workflow.py

Purpose: Execute the compiled workflow with input data.

Example:

python
Copy
from .json_to_langgraph import build_graph_from_json
from .graph_configs import self_Rag_Agent_config

app = build_graph_from_json(self_Rag_Agent_config)
app.invoke({"question": "What is LangGraph?"})
Folder Structure
Copy


JSONGraphBuilder/or/WorkflowRunner
├── graph_configs.json
├── workflow_functions.py (workflownodes)
├── chat_templates.py
├── llm_config.py
├── state_graphs.py
├── json_to_langgraph.py
├── function_registry.py
├── utils.py
├── run_workflow.py
└── README.md
└── sunWorkflowNodes.py (for subworkflow apps)