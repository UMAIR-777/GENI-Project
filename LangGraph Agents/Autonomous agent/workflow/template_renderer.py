from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import os
from typing import Dict, Any
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TemplateRenderer:
    """
    Manages prompt templates using the Jinja2 templating engine.
    
    @Feature: Prompt Template Rendering and Management
    @Scenario: Render prompt templates with correct context substitution and error handling
    """
    # def __init__(self):
    def __init__(self, template_folder: str = "prompts"):
        self.root_dir = Path(__file__).parent
        # self.prompts_dir = self.root_dir / "prompts"
        self.prompts_dir = self.root_dir / template_folder
        if not self.prompts_dir.exists():
            raise RuntimeError(f"Prompts directory not found at: {self.prompts_dir}")
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._cache: Dict[str, Any] = {}
        logger.info(f"TemplateRenderer initialized with prompts directory: {self.prompts_dir}")

    def get_template_path(self, template_name: str) -> str:
        """
        Convert a template name to the correct path by ensuring a '.jinja2' extension.
        
        @Feature: Prompt Template Rendering and Management
        @Scenario: Ensure proper template file path formatting
        
        Args:
            template_name (str): The input template file name.
            
        Returns:
            str: The properly formatted template file name.
        """
        if not template_name.endswith('.jinja2'):
            template_name = template_name.replace('.txt', '.jinja2')
        return template_name


    def render_prompt(self, template_path: str, **kwargs: Any) -> str:
        """
        Render a prompt template with the given context variables.
        
        @Feature: Prompt Template Rendering and Management
        @Scenario: Render prompt with accurate context substitution ensuring full template integrity
        
        Args:
            template_path (str): The name or path of the template file.
            **kwargs: Arbitrary context variables for template substitution.
        
        Returns:
            str: The rendered prompt string.
        
        Raises:
            TemplateNotFound: If the template file is not found.
            RuntimeError: If rendering fails.
        """
        try:
            template_path = self.get_template_path(template_path)
            if template_path not in self._cache:
                self._cache[template_path] = self.env.get_template(template_path)
                logger.debug(f"Loaded template: {template_path}")
            processed_kwargs = {}
            for key, value in kwargs.items():
                if hasattr(value, '__dict__'):
                    processed_kwargs[key] = value.__dict__
                elif isinstance(value, (dict, list)):
                    processed_kwargs[key] = json.dumps(value, indent=2)
                else:
                    processed_kwargs[key] = value
            rendered = self._cache[template_path].render(**processed_kwargs)
            if not rendered or not rendered.strip():
                raise RuntimeError("Rendered prompt is empty.")
            logger.debug(f"Template {template_path} rendered successfully.")
            return rendered
        except TemplateNotFound as e:
            logger.error(f"Template not found: {template_path}")
            raise
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {e}")
            raise RuntimeError(f"Error rendering template {template_path}: {e}") from e
