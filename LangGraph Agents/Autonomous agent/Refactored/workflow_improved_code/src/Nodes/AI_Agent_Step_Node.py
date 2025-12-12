import os
import json
import re
import time
import heapq
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from langchain_groq import ChatGroq

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom Exceptions
class ConfigError(Exception):
    pass

class JSONParseError(Exception):
    pass

class LLMInvocationError(Exception):
    pass

# Common Components and Types
class ConfigLoader:
    """
    Loads and validates environment configuration.
    @Feature EvalMetricsGeneration
    @Scenario DependencyValidation: Config Check
    """
    def __init__(self, env_path: str = '../.env'):
        if not os.path.isfile(env_path):
            logger.error(f".env file not found at {env_path}")
            raise ConfigError(f"Missing .env file at {env_path}")
        load_dotenv(dotenv_path=env_path)

    def get(self, key: str) -> str:
        val = os.getenv(key)
        if val is None:
            logger.error(f"Config key {key} not found")
            raise ConfigError(f"Missing config key: {key}")
        return val

class TemplateRenderer:
    """
    Renders Jinja2 templates.
    @Feature EvalMetricsGeneration
    @Scenario Happy Path Metric Generation
    """
    def __init__(self, template_dir: str):
        if not os.path.isdir(template_dir):
            logger.error(f"Template directory not found: {template_dir}")
            raise ConfigError(f"Template directory not found: {template_dir}")
        self.env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)

    def render(self, template_file: str, context: Dict[str, Any]) -> str:
        try:
            template = self.env.get_template(template_file)
        except TemplateNotFound:
            logger.error(f"Template not found: {template_file}")
            raise ConfigError(f"Template not found: {template_file}")
        return template.render(**context)

class JSONCleaner:
    """
    Cleans markdown fences from LLM outputs.
    @Feature EvalMetricsGeneration
    @Scenario Handles Invalid LLM Response
    """
    FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$")

    @staticmethod
    def clean(content: str) -> str:
        if not isinstance(content, str):
            logger.error("Content must be a string")
            raise JSONParseError("LLM output content is not a string")
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                return "\n".join(lines[1:-1]).strip()
        return text

class JSONParser:
    """
    Parses JSON strings into Python objects.
    @Feature EvalMetricsGeneration
    @Scenario Handles Invalid LLM Response
    """
    @staticmethod
    def parse(json_str: str) -> Any:
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"JSON parsing error: {e}")
            raise JSONParseError(f"Failed to parse JSON: {e}")

class MetricSelector:
    """
    Selects top-N metrics by insight_score efficiently.
    @Feature EvalMetricsGeneration
    @Scenario Partial Sort Optimization
    """
    @staticmethod
    def select(metrics: List[Dict[str, Any]], top_n: int) -> List[str]:
        if not isinstance(top_n, int) or top_n <= 0:
            logger.error("top_n must be a positive integer")
            raise ValueError("top_n must be a positive integer")
        if not metrics:
            return []
        # Use heapq.nlargest for O(n log k)
        top_metrics = heapq.nlargest(top_n, metrics, key=lambda x: x.get('insight_score', 0))
        return [m['metric'] for m in top_metrics]

class LLMInvoker:
    """
    Wraps ChatGroq invocation with retry, backoff, and failure handling.
    @Feature EvalMetricsGeneration
    @Scenario Chaos: Network Failure Recovery
    """
    def __init__(self, model: str, max_retries: int = 3, backoff_factor: float = 0.5):
        self.model = model
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def invoke(self, messages: List[Dict[str, str]]) -> str:
        attempt = 0
        while attempt < self.max_retries:
            try:
                llm = ChatGroq(temperature=0, model=self.model)
                response = llm.invoke(messages)
                content = getattr(response, 'content', '')
                if not content:
                    raise LLMInvocationError("Empty response from LLM")
                return content
            except Exception as e:
                attempt += 1
                wait = self.backoff_factor * (2 ** (attempt - 1))
                logger.warning(f"LLM invoke failed (attempt {attempt}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
        logger.error("Max retries reached for LLM invocation")
        raise LLMInvocationError("Failed to invoke LLM after retries")

# Production Quality Functions

def generate_eval_metrics(
    *,
    role: str,
    task: str,
    user_request: str,
    context: str = '',
    top_n: int = 7
) -> List[str]:
    """
    Generates and selects top evaluation metrics for a given role and task.

    @Feature EvalMetricsGeneration
    @Scenario Happy Path Metric Generation, Handles Invalid LLM Response, Partial Sort Optimization, DependencyValidation: Config Check, ModelBased LLM Invocation Flow

    Args:
        role: Non-empty user role string.
        task: Non-empty task description string.
        user_request: Non-empty request string.
        context: Optional context for metrics generation.
        top_n: Number of top metrics to select (positive integer).

    Returns:
        List of metric names sorted by descending insight score.

    Raises:
        ValueError: On invalid arguments.
        ConfigError: On missing config or template errors.
        JSONParseError: On JSON parsing failure.
        LLMInvocationError: On LLM invocation failure after retries.
    """
    # Input validation
    for name, val in [('role', role), ('task', task), ('user_request', user_request)]:
        if not isinstance(val, str) or not val.strip():
            logger.error(f"{name} must be a non-empty string")
            raise ValueError(f"{name} must be a non-empty string")
    if not isinstance(top_n, int) or top_n <= 0:
        logger.error("top_n must be a positive integer")
        raise ValueError("top_n must be a positive integer")

    # Load config and templates
    config_loader = ConfigLoader(env_path=os.getenv('DOTENV_PATH', '../.env'))
    model_name = config_loader.get('MODEL_USED')
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    renderer = TemplateRenderer(template_dir)

    # Prepare prompt
    tmpl_vars = {
        'Role': role,
        'Task': task,
        'User_Request': user_request,
        'Context': context,
        'THOUGHTS': [
            "Chain-of-Thought",
            "Input-Validation",
            "Output-Structure",
            "First-Principles-Buttons-Up",
            "Higher-Order-Top-Down",
            "Cross-Verification-Resilience-Thought",
            "Backward-Chaining-WorkBackwards-From-OutcomeThought",
            "BackTracking-Revise-Abandon-Failing-Solution-Path",
            "Hierarchical-Task-Decomposition-Sub-Goals",
            "Architecture-InterConnected-Components-Thought",
            "Sequence-Flow-Through",
            "Anti-Patterns-Likely-Thought",
            "Failure-Mode-Thought",
            "Hidden-Major-Bug-In-Code-Thought",
            "Robust-Risk-Mitigations-Thought",
            "Performance-Bottlenecks-Scalability-Thought",
            "Robust-Error-Handling-Thought",
            "Complex-Systems-Thinking",
            "Dependency-Chain-Thought",
            "Impact-Analysis-Thought",
            "Production-Configurability-Adaptability-Maintainability-Thought",
        ] 
    }
    prompt = renderer.render('eval_template.jinja2', tmpl_vars)

    # Invoke LLM
    llm_invoker = LLMInvoker(model=model_name)
    raw = llm_invoker.invoke([
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': 'Please output a JSON array named metrics.'}
    ])

    # Clean and parse
    clean = JSONCleaner.clean(raw)
    obj = JSONParser.parse(clean)
    if not isinstance(obj, dict) or 'metrics' not in obj:
        logger.error("Parsed JSON does not contain 'metrics'")
        raise JSONParseError("Missing 'metrics' key in response JSON")
    metrics = obj['metrics']
    if not isinstance(metrics, list):
        logger.error("'metrics' is not a list")
        raise JSONParseError("'metrics' must be a list of metric objects")

    # Select top metrics
    return MetricSelector.select(metrics, top_n)


def run_ai_step_node(
    *,
    role: str = "General Purpose Assistant",
    task: str = "General inquiry",
    context_window: int = 1024,
    user_request: str = "Hello,",
    context: str = '',
    model: str = "",
    top_metrics: int = 7
) -> str:
    """
    Generates eval metrics and runs an AI step node with structured prompts.

    @Feature EvalMetricsGeneration
    @Scenario ModelBased LLM Invocation Flow, Chaos: Network Failure Recovery

    Args:
        role: Role name string.
        task: Task description.
        context_window: Token limit for context.
        user_request: User's request content.
        context: Optional previous dialog context.
        model: Optional override model name.
        top_metrics: Number of top metrics to include.

    Returns:
        LLM-generated content for the given step.

    Raises:
        Propagates errors from generate_eval_metrics or LLMInvoker.
    """
    # Generate top eval metrics
    metrics_list = generate_eval_metrics(
        role=role,
        task=task,
        user_request=user_request,
        context=context,
        top_n=top_metrics
    )
    eval_str = ", ".join(metrics_list)
    logger.info(f"Top {top_metrics} Eval Metrics: {eval_str}")

    # Build system and user prompts
    system_prompt = (
        f"Role: {role}\nTask: {task}\nEval Metrics: {eval_str}\nContext Window: {context_window} tokens"
    )
    human_prompt = f"Request: {user_request}\nContext: {context}"

    # Optional task template
    try:
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        task_content = TemplateRenderer(template_dir).render(f"task_{role}.jinja2", {})
    except ConfigError:
        task_content = "1. Introduction\n2. Main Content\n3. Conclusion"

    messages = [
        { 'role': 'system', 'content': system_prompt },
        { 'role': 'system', 'content': task_content },
        { 'role': 'user', 'content': human_prompt },
    ]

    # Invoke LLM for step node
    invoker = LLMInvoker(model=model or os.getenv('MODEL_USED', ''))
    return invoker.invoke(messages)


if __name__ == "__main__":
    # Example tests for different roles/tasks
    scenarios = [
        {"role": "Data Analyst", "task": "Summarize quarterly sales performance", "user_request": "Provide a brief summary of Q1 sales.", "context": "Region: APAC; Product: Widgets."},
        {"role": "Technical Writer", "task": "Document API endpoints", "user_request": "Write docs for the new payment API endpoints.", "context": "Endpoints: /pay, /refund."},
    ]
    for sc in scenarios:
        print("\n--- Testing scenario ---")
        result = run_ai_step_node(
            role=sc["role"],
            task=sc["task"],
            context_window=512,
            user_request=sc["user_request"],
            context=sc["context"],
            top_metrics=5
        )
        print(result)
