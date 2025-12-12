from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import os
from typing import Dict, Any, Optional, Union
import logging
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
    TemplateNotFound,
    TemplateSyntaxError
)
import json
from markupsafe import Markup
import time
import threading

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class CacheEntry:
    """
    Represents a cached compiled Jinja2 template and its timestamp.
    """
    def __init__(self, template, timestamp: float):
        self.template = template
        self.timestamp = timestamp

class TemplateRenderer:
    """
    Manages prompt templates using the Jinja2 templating engine.
    
    @Feature: Prompt Template Rendering and Management
    @Scenario: Render prompt templates with correct context substitution and error handling
    """
    def __init__(
        self,
        template_folder: str = "prompts",  # Keep original parameter name for backwards compatibility
        cache_ttl: Optional[float] = None,
        autoescape_html: bool = True,
        prompts_dir: Optional[Union[str, Path]] = None  # Add new parameter as optional
    ):
        """
        Initialize the TemplateRenderer with backwards compatibility.
        
        Args:
            template_folder (str): Legacy parameter for template directory (default: "prompts")
            cache_ttl (Optional[float]): Cache time-to-live in seconds
            autoescape_html (bool): Enable HTML autoescaping
            prompts_dir (Optional[Union[str, Path]]): New parameter for template directory
        """
        # Use prompts_dir if provided, otherwise use legacy template_folder
        directory = prompts_dir if prompts_dir is not None else Path(__file__).parent / template_folder
        
        # Convert to Path object
        self.prompts_dir = Path(directory)
        
        # Validate directory
        if not self.prompts_dir.is_dir():
            raise RuntimeError(f"Prompts directory not found at: {self.prompts_dir}")

        # Configure Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=True if autoescape_html else False,  # Simplified autoescape setting
            # autoescape=select_autoescape(enabled_extensions=('html','xml')) if autoescape_html else None,
            trim_blocks=True,
            lstrip_blocks=True,
            enable_async=False
        )
        
        # JSON filter that outputs raw JSON without HTML escaping
        def safe_json_filter(value):
            return Markup(json.dumps(value, ensure_ascii=False))
        
        # Register the custom JSON filter
        self.env.filters['tojson'] = safe_json_filter

        # # JSON filter that outputs raw JSON without HTML escaping
        # self.env.filters['tojson'] = lambda v: json.dumps(v, ensure_ascii=False)

        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.cache_ttl = cache_ttl
        logger.info(f"TemplateRenderer initialized with prompts directory: {self.prompts_dir}")

    def get_template_path(self, template_name: str) -> str:
        """
        Normalize and validate template file name.

        @Feature: TemplateNameValidation
        @Scenario: TemplateNameValidation
        """
        if not isinstance(template_name, str):
            raise RuntimeError(f"Template name must be a string, got {type(template_name)}")
        name = template_name.strip()
        
        # Validate invalid characters (forward slash allowed only as path separator)
        invalid_chars = ['\\', ':', '*', '?', '"', '<', '>', '|']
        # Check each path component separately
        for part in name.split('/'):
            if any(char in part for char in invalid_chars):
                raise RuntimeError(f"Invalid character in template path component: {part}")
            
        # Convert to Path object for safe path handling
        path = Path(name)
        
        # Validate path components
        if any(part == '..' for part in path.parts):
            raise RuntimeError(f"Path traversal not allowed in template name: {name}")
        if any(part.startswith('.') for part in path.parts[1:]):
            raise RuntimeError(f"Hidden directories not allowed in template path: {name}")
            
        # Strip known extensions
        stem = path.stem
        for ext in ('.jinja2','.txt'):
            if stem.endswith(ext):
                stem = stem[:-len(ext)]
                
        # Reconstruct path with .jinja2 extension
        new_path = path.with_name(f"{stem}.jinja2")
        return str(new_path.as_posix())  # Use forward slashes consistently

    def _load_template(self, path: str):
        """
        Load and compile a template, handling IO and syntax errors.

        @Feature: TemplateLoader
        @Scenario: TemplateNotFound
        @Scenario: FSReadError
        @Scenario: SyntaxErrorInTemplate
        """
        template_file = self.prompts_dir / path
        # Pre-check file existence and permissions
        if not template_file.exists():
            logger.error(f"Template not found: {template_file}")
            raise TemplateNotFound(path)
        if not os.access(template_file, os.R_OK):
            logger.error(f"Permission denied reading template: {template_file}")
            raise PermissionError(f"Cannot read template file: {template_file}")
        if template_file.stat().st_size == 0:
            logger.error(f"Zero-byte template file: {template_file}")
            raise RuntimeError(f"Template file is empty: {path}")
        try:
            tmpl = self.env.get_template(path)
            logger.debug(f"Loaded template: {path}")
            return tmpl
        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error in {path}: {str(e)}")
            raise

    def _serialize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize context values for Jinja2 rendering.

        @Feature: ContextSerialization
        @Scenario: RenderWithDictContext
        @Scenario: RenderWithObjectContext
        @Scenario: RenderWithMixedContext
        """
        out: Dict[str, Any] = {}
        for k, v in context.items():
            if hasattr(v, '__dict__'):
                # Handle objects with dict attributes
                out[k] = v.__dict__
            elif isinstance(v, (dict, list, str, int, float, bool, type(None))):
                # Handle basic JSON-serializable types directly
                out[k] = v
            else:
                # Log and raise for unsupported types
                logger.error(f"Unsupported context type for key {k}: {type(v)}")
                raise RuntimeError(f"Unsupported context type for {k}: {type(v)}")
        return out

    def render_prompt(self, template_name: str, **kwargs: Any) -> str:
        """
        Render a template with context, using caching and validation.

        @Feature: TemplateRenderer Template Rendering and Management
        All Scenarios apply
        """
        path = self.get_template_path(template_name)
        now = time.time()
        with self._lock:
            entry = self._cache.get(path)
            if entry and self.cache_ttl and now - entry.timestamp > self.cache_ttl:
                logger.debug(f"Cache TTL expired for {path}")
                self._cache.pop(path, None)
                entry = None
            if not entry:
                tmpl = self._load_template(path)
                entry = CacheEntry(tmpl, now)
                self._cache[path] = entry
                logger.info(f"Loaded and cached template: {path}")
            template = entry.template
        # Serialize and render
        context = self._serialize_context(kwargs)
        try:
            rendered = template.render(**context)
            if not rendered or not rendered.strip():
                logger.error(f"Empty render result for template: {path}")
                raise RuntimeError(f"Empty render result for template: {path}")
            logger.debug(f"Rendered template successfully: {path}")
            return rendered
        except TemplateSyntaxError as e:
            # Invalidate cache on syntax errors
            with self._lock:
                self._cache.pop(path, None)
            logger.error(f"Template syntax error in {path}: {str(e)}")
            raise
        except Exception as e:
            # Invalidate cache on other errors
            with self._lock:
                self._cache.pop(path, None)
            logger.error(f"Error rendering template {path}: {str(e)}")
            raise

    def clear_cache(self, template_name: Optional[str]=None) -> None:
        """
        Clear cached templates.

        @Feature: ManualCacheClear
        @Scenario: ManualCacheClear
        """
        with self._lock:
            if template_name:
                path = self.get_template_path(template_name)
                self._cache.pop(path, None)
                logger.debug(f"Cache cleared for {path}")
            else:
                self._cache.clear()
                logger.debug("All cache entries cleared")

    def handle_file_change(self, template_name: str) -> None:
        """
        Invalidate cache entry for a template on file system change.

        @Feature: FileWatcherIntegration
        @Scenario: FileWatcherIntegration
        """
        path = self.get_template_path(template_name)
        self.clear_cache(path)
        # Clear Jinja internal cache if any
        try:
            self.env.cache.clear()
        except Exception:
            pass
        logger.info(f"Cache invalidated via file watcher for: {path}")
