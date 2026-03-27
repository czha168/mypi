"""Unit tests for prompt composition and template rendering."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from codepi.prompts.composer import PromptComposer, PromptConfig
from codepi.prompts.components import (
    PERSONA_BASE,
    PERSONA_MINIMAL,
    TOOL_USAGE_RULES,
    format_tool_descriptions,
    READ_ONLY_CONSTRAINTS,
    SAFETY_CONSTRAINTS,
    OUTPUT_EFFICIENCY,
)


class TestPromptConfig:
    """Tests for PromptConfig dataclass."""
    
    def test_default_config_creates_sections(self):
        """Default config should produce non-empty sections."""
        config = PromptConfig()
        sections = config.to_sections()
        assert len(sections) > 0
        assert all(s.strip() for s in sections)
    
    def test_custom_persona(self):
        """Custom persona should override default."""
        config = PromptConfig(persona="Custom assistant")
        sections = config.to_sections()
        assert "Custom assistant" in sections[0]
    
    def test_mode_constraints_injection(self):
        """Mode constraints should be included in sections."""
        config = PromptConfig(mode_constraints="PLAN MODE ACTIVE")
        sections = config.to_sections()
        assert "PLAN MODE ACTIVE" in "\n".join(sections)
    
    def test_skills_content_injection(self):
        """Skills content should be included in sections."""
        config = PromptConfig(skills_content="## Custom Skill\nDo something")
        sections = config.to_sections()
        assert "Custom Skill" in "\n".join(sections)
    
    def test_extra_sections_appended(self):
        """Extra sections should be appended at the end."""
        config = PromptConfig(extra_sections=["Extra section 1", "Extra section 2"])
        sections = config.to_sections()
        assert "Extra section 1" in sections
        assert "Extra section 2" in sections


class TestPromptComposer:
    """Tests for PromptComposer class."""
    
    def test_compose_returns_string(self):
        """compose() should return a non-empty string."""
        composer = PromptComposer()
        result = composer.compose()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_compose_uses_config(self):
        """compose() should use provided config."""
        composer = PromptComposer()
        config = PromptConfig(persona="TEST PERSONA")
        result = composer.compose(config)
        assert "TEST PERSONA" in result
    
    def test_compose_with_tools_injects_descriptions(self):
        """compose_with_tools() should inject tool descriptions."""
        # Create mock registry
        registry = MagicMock()
        registry.to_openai_schema.return_value = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool"
                }
            }
        ]
        
        composer = PromptComposer(tool_registry=registry)
        result = composer.compose_with_tools()
        
        assert "test_tool" in result
        assert "A test tool" in result
    
    def test_render_template_base_exists(self):
        """Base template should exist and render."""
        composer = PromptComposer()
        # base.yaml exists
        result = composer.render_template("base")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_render_template_missing_raises(self):
        """Missing template should raise FileNotFoundError."""
        composer = PromptComposer()
        with pytest.raises(FileNotFoundError):
            composer.render_template("nonexistent_template")
    
    def test_render_template_interpolation(self):
        """Template should interpolate {{var}} placeholders."""
        composer = PromptComposer()
        # Create a temporary template for testing
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "test.yaml"
            template_path.write_text("Hello {{name}}!")
            
            # Temporarily override template dir
            original_dir = composer.TEMPLATE_DIR
            composer.TEMPLATE_DIR = Path(tmpdir)
            composer.clear_cache()
            
            result = composer.render_template(
                "test", 
                variables={"name": "World"},
                strict=True
            )
            assert result == "Hello World!"
            
            composer.TEMPLATE_DIR = original_dir
    
    def test_render_template_missing_variable_strict(self):
        """Missing variable in strict mode should raise ValueError."""
        composer = PromptComposer()
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "test.yaml"
            template_path.write_text("Hello {{missing_var}}!")
            
            original_dir = composer.TEMPLATE_DIR
            composer.TEMPLATE_DIR = Path(tmpdir)
            composer.clear_cache()
            
            with pytest.raises(ValueError, match="missing_var"):
                composer.render_template("test", variables={}, strict=True)
            
            composer.TEMPLATE_DIR = original_dir
    
    def test_render_template_missing_variable_non_strict(self):
        """Missing variable in non-strict mode should keep placeholder."""
        composer = PromptComposer()
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "test.yaml"
            template_path.write_text("Hello {{missing_var}}!")
            
            original_dir = composer.TEMPLATE_DIR
            composer.TEMPLATE_DIR = Path(tmpdir)
            composer.clear_cache()
            
            result = composer.render_template(
                "test", 
                variables={}, 
                strict=False
            )
            assert "{{missing_var}}" in result
            
            composer.TEMPLATE_DIR = original_dir
    
    def test_template_caching(self):
        """Templates should be cached after first load."""
        composer = PromptComposer()
        
        # First load
        result1 = composer.render_template("base")
        assert "base" in composer._template_cache
        
        # Second load should use cache
        result2 = composer.render_template("base")
        assert result1 == result2
    
    def test_clear_cache(self):
        """clear_cache() should empty the template cache."""
        composer = PromptComposer()
        composer.render_template("base")
        assert len(composer._template_cache) > 0
        
        composer.clear_cache()
        assert len(composer._template_cache) == 0
    
    def test_from_registry_factory(self):
        """from_registry() should create bound composer."""
        registry = MagicMock()
        composer = PromptComposer.from_registry(registry)
        assert composer._tool_registry is registry


class TestFormatToolDescriptions:
    """Tests for format_tool_descriptions function."""
    
    def test_formats_single_tool(self):
        """Should format a single tool correctly."""
        schema = [
            {
                "type": "function",
                "function": {
                    "name": "read",
                    "description": "Read a file"
                }
            }
        ]
        result = format_tool_descriptions(schema)
        assert "### read" in result
        assert "Read a file" in result
    
    def test_formats_multiple_tools(self):
        """Should format multiple tools."""
        schema = [
            {
                "type": "function",
                "function": {"name": "read", "description": "Read file"}
            },
            {
                "type": "function",
                "function": {"name": "write", "description": "Write file"}
            }
        ]
        result = format_tool_descriptions(schema)
        assert "### read" in result
        assert "### write" in result
    
    def test_handles_missing_description(self):
        """Should handle tools without description."""
        schema = [
            {
                "type": "function",
                "function": {"name": "mystery"}
            }
        ]
        result = format_tool_descriptions(schema)
        assert "### mystery" in result
        assert "No description" in result
    
    def test_handles_empty_schema(self):
        """Should handle empty tool list."""
        result = format_tool_descriptions([])
        assert "## Available Tools" in result


class TestPromptComponents:
    """Tests for prompt component strings."""
    
    def test_persona_base_not_empty(self):
        """PERSONA_BASE should not be empty."""
        assert PERSONA_BASE.strip()
    
    def test_persona_minimal_not_empty(self):
        """PERSONA_MINIMAL should not be empty."""
        assert PERSONA_MINIMAL.strip()
    
    def test_tool_usage_rules_not_empty(self):
        """TOOL_USAGE_RULES should not be empty."""
        assert TOOL_USAGE_RULES.strip()
    
    def test_read_only_constraints_not_empty(self):
        """READ_ONLY_CONSTRAINTS should not be empty."""
        assert READ_ONLY_CONSTRAINTS.strip()
        assert "READ-ONLY" in READ_ONLY_CONSTRAINTS
    
    def test_safety_constraints_not_empty(self):
        """SAFETY_CONSTRAINTS should not be empty."""
        assert SAFETY_CONSTRAINTS.strip()
        assert "rm -rf" in SAFETY_CONSTRAINTS
    
    def test_output_efficiency_not_empty(self):
        """OUTPUT_EFFICIENCY should not be empty."""
        assert OUTPUT_EFFICIENCY.strip()
        assert "concise" in OUTPUT_EFFICIENCY.lower()
