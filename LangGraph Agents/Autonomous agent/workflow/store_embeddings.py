import os
import logging
from dotenv import load_dotenv
from database_manager import DatabaseManager
from embedding_service import EmbeddingService
import psycopg2

# Load environment variables
load_dotenv()

# Configure logging\logging.basicConfig(level=logging.INFO,
                    # format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection parameters from environment
db_config = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}


# Initialize DatabaseManager and EmbeddingService
embed_svc = EmbeddingService()
db = DatabaseManager(embed_svc)

if __name__ == '__main__':
    # Fetch all nodes from the available_nodes table
    nodes = db.fetch_nodes()
    logger.info(f"Fetched {len(nodes)} nodes from database for embedding generation.")

    # Generate and store embeddings for each node
    try:
        embed_svc.generate_and_store_node_embeddings(nodes)
        logger.info("Successfully generated and stored embeddings for all available nodes.")
    except psycopg2.Error as e:
        if e.pgcode == '42P01':
            logger.warning("node_embeddings table not found; skipping embedding storage.")
        else:
            logger.error(f"Critical database error during node embedding storage: {e}")
            raise
    except Exception as e:
        logger.error(f"Non-critical error during embedding generation: {e}")