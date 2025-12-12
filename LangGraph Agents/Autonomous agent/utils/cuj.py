import os
import json
import yaml
import logging

logger = logging.getLogger("uvicorn.error")

WORKFLOW_CONFIG_PATH = os.path.join("cuj_workflow", "config", "workflow_config.yaml")
OUTPUT_DIR = os.path.join("cuj_workflow", "output")


def get_workflow_config():
    try:
        with open(WORKFLOW_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading workflow config: {e}")
        return {}

workflow_config = get_workflow_config()

# Helper function to save data to JSON file
def save_to_json(data, filename, directory=None):
    if directory:
        file_path = os.path.join(directory, filename)
    else:
        file_path = os.path.join(OUTPUT_DIR, filename)
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Successfully saved data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {e}")
        return False

# Helper function to load data from JSON file
def load_from_json(filename, directory=None):
    if directory:
        file_path = os.path.join(directory, filename)
    else:
        file_path = os.path.join(OUTPUT_DIR, filename)
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error loading from {file_path}: {e}")
        return None

# Get list of workflow steps
def get_workflow_steps():
    if not workflow_config or "workflow" not in workflow_config:
        return []
    return [step.get("step") for step in workflow_config.get("workflow", [])]

# Get workflow step details by name
def get_step_by_name(step_name):
    if not workflow_config or "workflow" not in workflow_config:
        return None
    for step in workflow_config.get("workflow", []):
        if step.get("step") == step_name:
            return step
    return None