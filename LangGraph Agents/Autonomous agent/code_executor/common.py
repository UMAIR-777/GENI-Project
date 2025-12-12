# File: src/common.py
"""
Common Components and Types

Defines logging, custom exceptions, and utility functions.
"""

import logging
import jsonschema
from typing import Any, Dict

# Configure robust production logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AgenticWorkflow")

# Custom Exceptions for clear error signaling.
class InvalidInputError(Exception):
    """Raised when input validation fails."""
    pass

class ResourceNotFoundError(Exception):
    """Raised when a requested resource is not found."""
    pass

class DuplicateResourceError(Exception):
    """Raised when attempting to create a resource that already exists."""
    pass

def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    Validates that the input data adheres to the provided JSON schema.
    
    :param data: The JSON data to validate.
    :param schema: A JSON schema dict.
    :raises InvalidInputError: When data does not conform to the schema.
    
    @Feature Workflow Creation & Versioning
    @Scenario Creation fails with malformed JSON / Successfully create a workflow with valid input
    """
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as ve:
        logger.error("JSON Schema validation failed: %s", ve.message)
        raise InvalidInputError(f"JSON schema validation error: {ve.message}")
