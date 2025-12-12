from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from template_renderer import TemplateRenderer
from ai_service import AIService
from database_manager import DatabaseManager
from embedding_service import EmbeddingService
from node_service import NodeService
from workflow_planner import WorkflowPlanner
from workflow_generator import WorkflowGenerator
from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# --- Initialize all services globally (just like Flask) ---
model_name = os.getenv("MODEL_USED")
hf_api_token = os.getenv("HF_API_TOKEN")
if not model_name or not hf_api_token:
    raise ValueError("MODEL_USED and HF_API_TOKEN must be set in .env file.")

template_renderer = TemplateRenderer("prompts")
ai_service = AIService(model=model_name)
embedding_service = EmbeddingService()
database_manager = DatabaseManager(embedding_service)
database_manager.setup_database()
available_nodes = AVAILABLE_NODES

node_service = NodeService(
    embedding_service=embedding_service,
    database_manager=database_manager,
    template_renderer=template_renderer,
    ai_service=ai_service
)

workflow_planner = WorkflowPlanner(
    template_renderer=template_renderer,
    ai_service=ai_service,
    node_service=node_service,
    available_nodes=available_nodes
)

workflow_generator = WorkflowGenerator(
    ai_service, template_renderer, database_manager,
    embedding_service, workflow_planner, node_service
)

# --- Define Pydantic model for incoming request ---
class WorkflowRequest(BaseModel):
    query: str

# --- FastAPI endpoint ---
@app.post("/generate_workflow")
def generate_workflow(request: WorkflowRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="No query provided")

    final_workflow, missing_nodes = workflow_generator.generate_workflow(request.query)

    if missing_nodes:
        return {
            "status": "incomplete",
            "missing_nodes": missing_nodes
        }

    if final_workflow:
        return {
            "status": "success",
            "workflow": final_workflow
        }

    raise HTTPException(status_code=500, detail="No workflow could be generated")
