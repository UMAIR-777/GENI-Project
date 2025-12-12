# import os
# from dotenv import load_dotenv
# from huggingface_hub import InferenceClient
# from sentence_transformers import SentenceTransformer
# import numpy as np
# from typing import List, Union
# import json
# import logging

# # Import our refactored classes
# from template_renderer import TemplateRenderer
# from ai_service import AIService
# from database_manager import DatabaseManager
# from embedding_service import EmbeddingService
# from node_service import NodeService
# from workflow_planner import WorkflowPlanner
# from workflow_generator import WorkflowGenerator
# from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES
# # Load environment variables
# load_dotenv()

# def main():
#     model_name = os.getenv("MODEL_USED")
#     hf_api_token = os.getenv("HF_API_TOKEN")
#     # if not model_name or not hf_api_token:
#     if not model_name or not hf_api_token:
#         print("MODEL_NAME and HF_API_TOKEN must be set in the .env file.")
#         return

#     # client = InferenceClient(token=hf_api_token) # Use this when you want to use HF API
#     template_renderer = TemplateRenderer("prompts")
#     ai_service = AIService(model=model_name)
#     # Use local embedding model
#     # client = InferenceClient(token=hf_api_token) # Set client to None when using local model
#     client = None  # Set client to None when using local model
#     # embedding_service = EmbeddingService(client=client)

#     # Initialize node service with available nodes
#     # node_service = NodeService()
#     embedding_service = EmbeddingService()  # Uses default API URL or specify custom one
    
#     # Now, pass embedding_service into DatabaseManager
#     database_manager = DatabaseManager(embedding_service)

#     # Get available nodes from your DATA_FOLDER
#     available_nodes = AVAILABLE_NODES  # Import this from DATA_FOLDER.save_available_nodes


#     node_service = NodeService(
#         embedding_service=embedding_service,
#         database_manager=database_manager,
#         template_renderer=template_renderer,
#         ai_service=ai_service
#     )
#     # workflow_planner = WorkflowPlanner(template_renderer, ai_service, node_service)
#     workflow_planner = WorkflowPlanner(
#         template_renderer=template_renderer,
#         ai_service=ai_service,
#         node_service=node_service,
#         available_nodes=available_nodes
#     )
#     workflow_generator = WorkflowGenerator(
#         ai_service, template_renderer, database_manager, embedding_service, workflow_planner, node_service
#     )

#     # Set up the database
#     database_manager.setup_database()

#     # Example user task
#     # user_task_query = ("i want to scrape the websites, extract keywords, summarize the content.")
#     user_task_query = ("need a workflow that processes a YouTube video for marketing analysis. which summerize the video content and generate keywords from the transcript and in the end, write blog.")
#     # user_task_query = ("i want to analyze the image and summarize the scence and create the blog content.")
#     # user_task_query = ("i want to scrape the websites, extract keywords, summarize the content and write SEO Optimized blog.")

#     # try:
#     #     database_manager.store_available_nodes(AVAILABLE_NODES)
#     # except Exception as e:
#     #     logger.warning(f"Node storage warning (may already exist): {e}")

#     final_workflow, missing_nodes = workflow_generator.generate_workflow(user_task_query)
#     if missing_nodes:
#         print("\nMissing Nodes Detected:")
#         print(json.dumps(missing_nodes, indent=2))
#         print("\nPlease add the missing nodes before proceeding.")
#     elif final_workflow:
#         print("\nWorkflow Generation Results:")
#         print(final_workflow)  # Already formatted with indent=2
#     else:
#         print("\nNo workflow could be generated.")

# if __name__ == "__main__":
#     main()
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import json
import logging

# Import our refactored classes
from template_renderer import TemplateRenderer
from ai_service import AIService
from database_manager import DatabaseManager
# from embedding_service import EmbeddingService  # Commented out local embedding service
from embedding_service import EmbeddingService  # New API-based embedding service
from node_service import NodeService
from workflow_planner import WorkflowPlanner
from workflow_generator import WorkflowGenerator
from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES
# Load environment variables
load_dotenv()

def main():
    model_name = os.getenv("MODEL_USED")
    hf_api_token = os.getenv("HF_API_TOKEN")
    if not model_name or not hf_api_token:
        print("MODEL_NAME and HF_API_TOKEN must be set in the .env file.")
        return

    template_renderer = TemplateRenderer("prompts")
    ai_service = AIService(model=model_name)

    # Use API-based embedding service instead of local model
    embedding_service = EmbeddingService()  # Uses API URL from .env or default

    # Now, pass embedding_service into DatabaseManager
    database_manager = DatabaseManager(embedding_service)

    # Get available nodes from your DATA_FOLDER
    available_nodes = AVAILABLE_NODES  # Import this from DATA_FOLDER.save_available_nodes

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
        ai_service, template_renderer, database_manager, embedding_service, workflow_planner, node_service
    )

    # Set up the database
    database_manager.setup_database()
    user_task_query = ("Run full ETL pipeline on customer database")

#"Run full ETL pipeline on customer database"

#"Process customer data from source to target database")
    #user_task_query = ("need a workflow that processes a YouTube video for marketing analysis. which summerize the video content and generate keywords from the transcript and in the end, write blog.")
    # user_task_query = ("i need a workflow that analyze the image and create the blog post.")

    final_workflow, missing_nodes = workflow_generator.generate_workflow(user_task_query)
    if missing_nodes:
        print("\nMissing Nodes Detected:")
        print(json.dumps(missing_nodes, indent=2))
        print("\nPlease add the missing nodes before proceeding.")
    elif final_workflow:
        print("\nWorkflow Generation Results:")
        print(final_workflow)  # Already formatted with indent=
    else:
        print("\nNo workflow could be generated.")

if __name__ == "__main__":
    main()
