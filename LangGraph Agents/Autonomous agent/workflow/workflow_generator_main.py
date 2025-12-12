import os
from typing import List, Optional
from dotenv import load_dotenv
import json
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import our refactored classes
from .template_renderer import TemplateRenderer
from .ai_service import AIService
from .database_manager import DatabaseManager
from .embedding_service import EmbeddingService
from .node_service import NodeService
from .workflow_planner import WorkflowPlanner
from .workflow_generator import WorkflowGenerator
from .DATA_FOLDER.save_available_nodes import AVAILABLE_NODES




class Workflow_generator_v1:
    def __init__(self, user_task: str, allowed_nodes: Optional[List[str]] = None):
       # store the incoming request and any node‐filtering list
        self.user_task = user_task
        self.allowed_nodes = allowed_nodes


    def generate_workflow_v1(self):
        # Core model identifiers
        model_name = os.getenv("MODEL_USED")

        # Ensure required environment variables are set
        if not model_name:
            print("Error: MODEL_USED must be set in the .env file.")
            return

        logger.info(f"Using AI model: {model_name}")
        # Initialize core components
        template_renderer = TemplateRenderer("prompts")
        ai_service = AIService(model=model_name)

        # Use local embedding model only
        embedding_service = EmbeddingService()
        database_manager = DatabaseManager(embedding_service)

        node_service = NodeService(
            embedding_service=embedding_service,
            database_manager=database_manager,
            template_renderer=template_renderer,
            ai_service=ai_service
        )
        workflow_planner = WorkflowPlanner(template_renderer, ai_service, node_service,database_manager)
        workflow_generator = WorkflowGenerator(
            ai_service,
            template_renderer,
            database_manager,
            embedding_service,
            workflow_planner,
            node_service
        )


        # Prepare database schema
        database_manager.setup_database()

        # # Example user task query
        # user_task_query = (
        #     "i want to scrape the websites, extract keywords, SEO strategy the content."
        # )
        # Generate and display workflow
        # pass along the stored parameters
        workflow_json, orig_user_task, descriptions, tags, spo, status = workflow_generator.generate_workflow(self.user_task, self.allowed_nodes)


        # if workflow_response :
        #     print("Workflow Generation Results:")
        #     print(json.dumps(final_workflow, indent=4))
        #     if missing_nodes:
        #         print("Missing Nodes:")
        #         print(json.dumps(missing_nodes, indent=2))

        return workflow_json, orig_user_task, descriptions, tags, spo,status

# if __name__ == "__main__":
#     main()


