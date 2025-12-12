# File: agent_framework.py
import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from langchain_groq import ChatGroq

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Exceptions
class ConfigError(Exception): pass
class TemplateError(Exception): pass
class LLMError(Exception): pass

# Config loader
def load_config(env_path: str = '.env') -> Dict[str, str]:
    if not os.path.isfile(env_path):
        raise ConfigError(f".env not found at {env_path}")
    load_dotenv(env_path)
    api_key = os.getenv('GROQ_API_KEY')
    model   = os.getenv('MODEL_USED')
    if not api_key or not model:
        raise ConfigError("GROQ_API_KEY and MODEL_USED must be set in .env")
    return {'api_key': api_key, 'model': model}

# Template renderer
def render_template(template_path: str, context: Dict[str, Any]) -> str:
    """Renders a Jinja2 template given full path."""
    directory, filename = os.path.split(template_path)
    if not os.path.isdir(directory):
        raise TemplateError(f"Template dir not found: {directory}")
    env = Environment(loader=FileSystemLoader(directory), autoescape=False)
    try:
        tmpl = env.get_template(filename)
    except TemplateNotFound:
        raise TemplateError(f"Template not found: {filename}")
    return tmpl.render(**context)

# LLM invoker
def invoke_llm(api_key: str, model: str, messages: List[Dict[str, str]], retries: int = 3, backoff: float = 0.5) -> str:
    attempt = 0
    while attempt < retries:
        try:
            llm = ChatGroq(api_key=api_key, temperature=0, model=model)
            resp = llm.invoke(messages)
            content = getattr(resp, 'content', '')
            if not content:
                raise LLMError("Empty response from LLM")
            return content
        except Exception as e:
            attempt += 1
            if attempt >= retries:
                raise LLMError(f"Failed after {retries} retries: {e}")
            wait = backoff * (2 ** (attempt - 1))
            logger.warning(f"LLM invoke failed (attempt {attempt}): {e}. Retrying in {wait}s...")
            time.sleep(wait)

# Agent step runner
def run_agent_step(
    role: str = "Code Writer",
    task: str = "bdd_generate",
    user_request: str = "",
    eval_metrics: str = "",
    context_window: int = 1024,
    model: Optional[str] = None,
    template_root: str = 'templates',
    env_path: str = '.env'
) -> Dict[str, Any]:
    """
    Executes one step for a given agent node with configurable evaluation metrics:
    - role: the agent identifier (e.g., code_writer)
    - task: the phase/template name (e.g., bdd_generate, bdd_eval)
    - user_request: user input or requirement text
    - eval_metrics: optional eval metrics or feedback from previous pass
    - context_window: token/context limit
    - model: override model name
    - template_root: path to templates directory
    - env_path: path to .env file for config

    Returns a dict with:
      {
        'response': LLM content,
      }
    """
    # Load config
    cfg = load_config(env_path)
    api_key = cfg['api_key']
    llm_model = model or cfg['model']

    # Determine template path
    tpl_path = os.path.join(template_root, role, f"{role}_{task}.jinja2")

    # Build context for template
    context: Dict[str, Any] = {
        'role': role,
        'task': task,
        'user_request': user_request,
        'eval_metrics': eval_metrics,
        'context_window': context_window
    }

    # Render and invoke
    prompt = render_template(tpl_path, context)
    messages = [
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': user_request}
    ]
    response = invoke_llm(api_key=api_key, model=llm_model, messages=messages)

    return {
        'response': response,
    }

# CLI example
if __name__ == '__main__':
    outputs = run_agent_step(
        role='code_writer',
        task='bdd_generate',
        user_request='merge_sorted_lists_unique',
        eval_metrics='bdd_eval',
        context_window=512,
        model=None,
        template_root=os.path.join(os.path.dirname(__file__), 'templates'),
        env_path=os.path.join(os.path.dirname(__file__), '.env')
    )
    print(json.dumps(outputs, indent=2))
