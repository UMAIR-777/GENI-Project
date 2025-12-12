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
    def __init__(self, model: str = None, temperature: float = 0.0):
        """
        Initialize the AIService with a model and temperature.
        @Feature 'Configuration Validation'
        @Scenario 'MissingEnvVar'
        """
        if model is None:
            model = os.getenv("MODEL_USED")
            if not model:
                raise EnvironmentError("Environment variable 'MODEL_USED' must be set for LLM configuration.")
        self.llm = ChatGroq(temperature=temperature, model=model)

    def ask_ai(self, prompt: str, context: str = "Return valid JSON") -> str:
        """
        Invoke the LLM with a prompt and context.
        @Feature 'JSON Extraction Accuracy'
        @Scenario 'NoJSONStructure'
        @Feature 'Error Handling Robustness'
        @Scenario 'LLMInvocationFailure'
        @Feature 'Input Validation'
        @Scenario 'PromptEmpty'
        @Feature 'Performance Optimization'
        @Scenario 'StreamingFallback'
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("Context must be a non-empty string.")
        
        messages = [("system", prompt), ("human", f"<context>\n{context}\n</context>")]
        
        try:
            response = self.llm.invoke(messages)
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise RuntimeError("LLM invocation failed.") from e

        if not response or not hasattr(response, "content"):
            logger.error("LLM response is empty or lacks a 'content' attribute.")
            raise RuntimeError("Invalid LLM response received.")

        raw_response = response.content
        match = re.search(r'(\{.*\}|\[.*\])', raw_response, re.DOTALL)
        if not match:
            logger.error("No JSON structure found in LLM response.")
            raise RuntimeError("Failed to extract JSON from LLM response.")
        
        json_str = match.group(0)
        try:
            import json
            json.loads(json_str)
        except Exception as e:
            logger.error(f"Extracted JSON is invalid: {e}")
            raise RuntimeError("Extracted JSON is invalid.") from e

        return json_str