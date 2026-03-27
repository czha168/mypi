"""Prompt composition and template rendering system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from codepi.prompts.components import (
    PERSONA_BASE,
    TOOL_USAGE_RULES,
    SAFETY_CONSTRAINTS,
    OUTPUT_EFFICIENCY,
    format_tool_descriptions,
)

if TYPE_CHECKING:
    from codepi.tools.base import ToolRegistry


@dataclass
class PromptConfig:
    """Configuration for prompt composition."""
    
    persona: str = PERSONA_BASE
    tool_rules: str = TOOL_USAGE_RULES
    constraints: str = SAFETY_CONSTRAINTS
    efficiency: str = OUTPUT_EFFICIENCY
    mode_constraints: str = ""  # Additional mode-specific constraints
    skills_content: str = ""    # Injected skills content
    extra_sections: list[str] = field(default_factory=list)
    
    def to_sections(self) -> list[str]:
        """Convert config to list of prompt sections."""
        sections = [
            self.persona,
            self.tool_rules,
            self.constraints,
        ]
        if self.mode_constraints:
            sections.append(self.mode_constraints)
        sections.append(self.efficiency)
        if self.skills_content:
            sections.append(self.skills_content)
        sections.extend(self.extra_sections)
        return [s for s in sections if s.strip()]


class PromptComposer:
    """Composes system prompts from modular components with template support."""
    
    TEMPLATE_DIR = Path(__file__).parent / "templates"
    
    def __init__(self, tool_registry: ToolRegistry | None = None):
        """Initialize prompt composer.
        
        Args:
            tool_registry: Tool registry for tool description interpolation
        """
        self._tool_registry = tool_registry
        self._template_cache: dict[str, str] = {}
    
    def compose(self, config: PromptConfig | None = None) -> str:
        """Compose a system prompt from components.
        
        Args:
            config: Prompt configuration, uses defaults if None
            
        Returns:
            Composed system prompt string
        """
        if config is None:
            config = PromptConfig()
        return "\n\n".join(config.to_sections())
    
    def render_template(
        self, 
        template_name: str, 
        variables: dict[str, str] | None = None,
        strict: bool = False,
    ) -> str:
        """Render a YAML template with variable interpolation.
        
        Args:
            template_name: Name of template file (without .yaml extension)
            variables: Variables to interpolate ({{var}} syntax)
            strict: If True, raise error for missing variables
            
        Returns:
            Rendered template content
            
        Raises:
            FileNotFoundError: Template file not found
            ValueError: Missing required variable in strict mode
        """
        template = self._load_template(template_name)
        return self._interpolate(template, variables or {}, strict)
    
    def compose_with_tools(self, config: PromptConfig | None = None) -> str:
        """Compose system prompt with tool descriptions injected.
        
        Args:
            config: Prompt configuration
            
        Returns:
            Composed system prompt with formatted tool descriptions
        """
        if config is None:
            config = PromptConfig()
        
        sections = config.to_sections()
        
        # Inject tool descriptions if registry available
        if self._tool_registry:
            tools_desc = format_tool_descriptions(
                self._tool_registry.to_openai_schema()
            )
            # Insert tool descriptions after persona
            sections.insert(1, tools_desc)
        
        return "\n\n".join(sections)
    
    def _load_template(self, name: str) -> str:
        """Load template from disk with caching.
        
        Args:
            name: Template name (without extension)
            
        Returns:
            Template content
        """
        if name not in self._template_cache:
            template_path = self.TEMPLATE_DIR / f"{name}.yaml"
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")
            self._template_cache[name] = template_path.read_text()
        return self._template_cache[name]
    
    def _interpolate(
        self, 
        template: str, 
        variables: dict[str, str], 
        strict: bool,
    ) -> str:
        """Interpolate {{var}} placeholders in template.
        
        Args:
            template: Template string with {{var}} placeholders
            variables: Variable name to value mapping
            strict: Raise error for missing variables
            
        Returns:
            Interpolated string
        """
        pattern = r'\{\{(\w+)\}\}'
        
        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name in variables:
                return variables[var_name]
            if strict:
                raise ValueError(f"Missing template variable: {var_name}")
            return match.group(0)  # Keep placeholder if not strict
        
        return re.sub(pattern, replacer, template)
    
    def clear_cache(self) -> None:
        """Clear template cache."""
        self._template_cache.clear()
    
    @classmethod
    def from_registry(cls, registry: ToolRegistry) -> "PromptComposer":
        """Create composer bound to a tool registry.
        
        Args:
            registry: Tool registry for tool descriptions
            
        Returns:
            Configured PromptComposer
        """
        return cls(tool_registry=registry)


def load_template_file(path: Path | str) -> dict:
    """Load and parse a YAML template file.
    
    Args:
        path: Path to YAML file
        
    Returns:
        Parsed YAML as dictionary
    """
    return yaml.safe_load(Path(path).read_text())
