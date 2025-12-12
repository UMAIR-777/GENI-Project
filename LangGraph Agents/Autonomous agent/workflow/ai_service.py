import os
import re
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load environment variables and validate configuration
load_dotenv()
class AIService:
    """
    Wraps the ChatGroq language model interactions.
    """
    def __init__(self, model: str = None, temperature: int = 0):
        if model is None:
            model = os.getenv("MODEL_USED")
            if not model:
                raise EnvironmentError("Environment variable 'MODEL_USED' must be set for LLM configuration.")
        self.llm = ChatGroq(temperature=temperature, model=model)

    def ask_ai(self, prompt: str, context: str = "Return valid JSON") -> str:

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("Context must be a non-empty string.")
        
        messages = [("system", prompt), ("human", f"<context>\n{context}\n</context>")]
        
        try:
            response = self.llm.invoke(messages)
        except Exception as e:
            # logger.error(f"LLM invocation failed: {e}")
            raise RuntimeError("LLM invocation failed.") from e

        if not response or not hasattr(response, "content"):
            # logger.error("LLM response is empty or lacks a 'content' attribute.")
            raise RuntimeError("Invalid LLM response received.")

        raw_response = response.content
        match = re.search(r'(\{.*\}|\[.*\])', raw_response, re.DOTALL)
        if not match:
            # logger.error("No JSON structure found in LLM response.")
            raise RuntimeError("Failed to extract JSON from LLM response.")
        
        json_str = match.group(0)
        try:
            import json
            json.loads(json_str)
        except Exception as e:
            # logger.error(f"Extracted JSON is invalid: {e}")
            raise RuntimeError("Extracted JSON is invalid.") from e

        return json_str

    def get_database_pool(self):
        """
        Retrieves the database connection pool.
        """
        pool = self.database_manager.get_db_pool()
        if pool is None:
            # Initialize pool if not done
            from database_manager import setup_database
