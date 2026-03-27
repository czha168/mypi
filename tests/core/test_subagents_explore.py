"""Unit tests for explore subagent."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from codepi.core.subagent import SubagentConfig, SubagentResult, SubagentStatus
from codepi.core.subagents.explore import (
    ExploreSubagentConfig,
    EXPLORE_SYSTEM_PROMPT,
    run_explore_subagent,
)


class TestExploreSubagentConfig:
    """Tests for ExploreSubagentConfig."""
    
    def test_create_returns_valid_config(self):
        """Test that create() returns a valid SubagentConfig."""
        config = ExploreSubagentConfig.create()
        
        assert isinstance(config, SubagentConfig)
        assert config.name == "explore"
        assert config.read_only is True
        assert config.max_turns == 10
        assert config.timeout_seconds == 300.0
    
    def test_tool_whitelist_enforced(self):
        """Test that only whitelisted tools are available."""
        config = ExploreSubagentConfig.create()
        
        # Allowed tools
        assert "read" in config.tools
        assert "find" in config.tools
        assert "grep" in config.tools
        assert "ls" in config.tools
        assert "bash" in config.tools
        
        # Disallowed tools
        assert "write" not in config.tools
        assert "edit" not in config.tools
    
    def test_system_prompt_contains_read_only_directive(self):
        """Test that system prompt emphasizes read-only mode."""
        config = ExploreSubagentConfig.create()
        
        assert "READ-ONLY" in config.system_prompt
        assert "NO FILE MODIFICATIONS" in config.system_prompt
    
    def test_system_prompt_contains_efficiency_directive(self):
        """Test that system prompt contains efficiency directive."""
        assert "fast agent" in EXPLORE_SYSTEM_PROMPT.lower()
        assert "quickly as possible" in EXPLORE_SYSTEM_PROMPT.lower()
    
    def test_system_prompt_prohibits_modifications(self):
        """Test that system prompt explicitly prohibits file modifications."""
        prompt = EXPLORE_SYSTEM_PROMPT.lower()
        
        assert "not have access to file editing tools" in prompt
        assert "strictly prohibited" in prompt


class TestExploreSystemPrompt:
    """Tests for explore system prompt content."""
    
    def test_contains_parallel_execution_guidance(self):
        """Test that prompt encourages parallel tool calls."""
        assert "parallel" in EXPLORE_SYSTEM_PROMPT.lower()
    
    def test_contains_absolute_path_guidance(self):
        """Test that prompt requires absolute paths in results."""
        assert "absolute paths" in EXPLORE_SYSTEM_PROMPT.lower()
    
    def test_contains_read_only_bash_list(self):
        """Test that prompt lists allowed read-only bash commands."""
        assert "ls" in EXPLORE_SYSTEM_PROMPT
        assert "git status" in EXPLORE_SYSTEM_PROMPT
        assert "git log" in EXPLORE_SYSTEM_PROMPT
        assert "git diff" in EXPLORE_SYSTEM_PROMPT
    
    def test_contains_blocked_bash_list(self):
        """Test that prompt lists blocked bash commands."""
        prompt_lower = EXPLORE_SYSTEM_PROMPT.lower()
        
        assert "mkdir" in prompt_lower
        assert "rm" in prompt_lower
        assert "git add" in prompt_lower
        assert "git commit" in prompt_lower


class TestRunExploreSubagent:
    """Tests for run_explore_subagent function."""
    
    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.stream = AsyncMock()
        return provider
    
    @pytest.fixture
    def mock_session_manager(self):
        sm = MagicMock()
        sm.new_session = MagicMock(return_value="test-session-id")
        return sm
    
    @pytest.fixture
    def mock_tool_registry(self):
        from codepi.tools.base import ToolRegistry, Tool, ToolResult
        
        # Create a real registry with mock tools
        registry = ToolRegistry()
        
        for tool_name in ["read", "find", "grep", "ls", "bash"]:
            mock_tool = MagicMock(spec=Tool)
            mock_tool.name = tool_name
            mock_tool.description = f"Mock {tool_name} tool"
            mock_tool.input_schema = {"type": "object", "properties": {}}
            mock_tool.execute = AsyncMock(return_value=ToolResult(output="mock output"))
            mock_tool.to_openai_schema = MagicMock(return_value={
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"Mock {tool_name} tool",
                    "parameters": {}
                }
            })
            registry.register(mock_tool)
        
        return registry
    
    @pytest.fixture
    def runner(self, mock_provider, mock_session_manager, mock_tool_registry):
        from codepi.core.subagent import SubagentRunner
        
        return SubagentRunner(
            provider=mock_provider,
            session_manager=mock_session_manager,
            model="test-model",
            tool_registry=mock_tool_registry,
        )
    
    @pytest.mark.asyncio
    async def test_returns_subagent_result(self, runner):
        """Test that run_explore_subagent returns SubagentResult."""
        from codepi.ai.provider import DoneEvent, TokenUsage
        
        # Mock the provider to return a simple response
        async def mock_stream(*args, **kwargs):
            yield DoneEvent(usage=TokenUsage(input_tokens=10, output_tokens=5))
        
        runner._provider.stream = mock_stream
        
        result = await run_explore_subagent(runner, "Find all Python files")
        
        assert isinstance(result, SubagentResult)
    
    @pytest.mark.asyncio
    async def test_uses_explore_config(self, runner):
        """Test that run_explore_subagent uses explore config."""
        from codepi.ai.provider import DoneEvent, TokenUsage
        
        streamed_system = None
        
        async def mock_stream(*args, **kwargs):
            nonlocal streamed_system
            streamed_system = kwargs.get("system")
            yield DoneEvent(usage=TokenUsage(input_tokens=10, output_tokens=5))
        
        runner._provider.stream = mock_stream
        
        await run_explore_subagent(runner, "Test prompt")
        
        # The system prompt should contain explore-specific content
        assert streamed_system is not None
        assert "file search specialist" in streamed_system.lower()


class TestExploreReadOnlyConstraints:
    """Tests for read-only constraints in explore subagent."""
    
    def test_config_is_read_only(self):
        """Test that explore config has read_only=True."""
        config = ExploreSubagentConfig.create()
        assert config.read_only is True
    
    def test_no_write_tool(self):
        """Test that write tool is not in whitelist."""
        config = ExploreSubagentConfig.create()
        assert "write" not in config.tools
    
    def test_no_edit_tool(self):
        """Test that edit tool is not in whitelist."""
        config = ExploreSubagentConfig.create()
        assert "edit" not in config.tools
    
    def test_bash_is_readonly_wrapped(self):
        """Test that bash tool will be wrapped for read-only mode."""
        from codepi.core.subagent import SubagentRunner, ReadOnlyBashFilter
        
        # The runner should wrap bash in read-only mode
        # This is verified by checking ReadOnlyBashFilter behavior
        filter = ReadOnlyBashFilter()
        
        # Read-only commands should be allowed
        assert filter.is_allowed("ls -la")[0]
        assert filter.is_allowed("git status")[0]
        assert filter.is_allowed("find . -name '*.py'")[0]
        
        # Write commands should be blocked
        assert not filter.is_allowed("rm -rf /tmp")[0]
        assert not filter.is_allowed("mkdir test")[0]
        assert not filter.is_allowed("git add .")[0]
