"""Unit tests for plan subagent."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from codepi.core.subagent import SubagentConfig, SubagentResult, SubagentStatus
from codepi.core.subagents.plan import (
    PlanSubagentConfig,
    PLAN_SYSTEM_PROMPT,
    run_plan_subagent,
)


class TestPlanSubagentConfig:
    """Tests for PlanSubagentConfig."""
    
    def test_create_returns_valid_config(self):
        """Test that create() returns a valid SubagentConfig."""
        config = PlanSubagentConfig.create()
        
        assert isinstance(config, SubagentConfig)
        assert config.name == "plan"
        assert config.read_only is True
        assert config.max_turns == 15
        assert config.timeout_seconds == 600.0
    
    def test_tool_whitelist_enforced(self):
        """Test that only whitelisted tools are available."""
        config = PlanSubagentConfig.create()
        
        assert "read" in config.tools
        assert "find" in config.tools
        assert "grep" in config.tools
        assert "ls" in config.tools
        assert "bash" in config.tools
        
        assert "write" not in config.tools
        assert "edit" not in config.tools
    
    def test_system_prompt_contains_read_only_directive(self):
        """Test that system prompt emphasizes read-only mode."""
        config = PlanSubagentConfig.create()
        
        assert "READ-ONLY" in config.system_prompt
        assert "NO FILE MODIFICATIONS" in config.system_prompt
    
    def test_longer_timeout_than_explore(self):
        """Test that plan has longer timeout than explore."""
        from codepi.core.subagents.explore import ExploreSubagentConfig
        
        plan_config = PlanSubagentConfig.create()
        explore_config = ExploreSubagentConfig.create()
        
        assert plan_config.timeout_seconds > explore_config.timeout_seconds
    
    def test_more_turns_than_explore(self):
        """Test that plan has more turns than explore."""
        from codepi.core.subagents.explore import ExploreSubagentConfig
        
        plan_config = PlanSubagentConfig.create()
        explore_config = ExploreSubagentConfig.create()
        
        assert plan_config.max_turns > explore_config.max_turns


class TestPlanSystemPrompt:
    """Tests for plan system prompt content."""
    
    def test_contains_structured_process(self):
        """Test that prompt outlines structured planning process."""
        prompt_lower = PLAN_SYSTEM_PROMPT.lower()
        
        assert "understand" in prompt_lower
        assert "explore" in prompt_lower
        assert "design" in prompt_lower
    
    def test_contains_critical_files_section(self):
        """Test that prompt requires critical files output."""
        assert "Critical Files for Implementation" in PLAN_SYSTEM_PROMPT
        assert "3-5 files" in PLAN_SYSTEM_PROMPT
    
    def test_contains_trade_offs_guidance(self):
        """Test that prompt mentions trade-offs."""
        assert "trade-off" in PLAN_SYSTEM_PROMPT.lower()
    
    def test_contains_pattern_reuse_guidance(self):
        """Test that prompt encourages pattern reuse."""
        prompt_lower = PLAN_SYSTEM_PROMPT.lower()
        
        assert "existing pattern" in prompt_lower or "reuse" in prompt_lower
    
    def test_contains_implementation_order_guidance(self):
        """Test that prompt mentions implementation sequencing."""
        assert "sequencing" in PLAN_SYSTEM_PROMPT.lower() or "order" in PLAN_SYSTEM_PROMPT.lower()
    
    def test_contains_challenge_anticipation(self):
        """Test that prompt mentions anticipating challenges."""
        prompt_lower = PLAN_SYSTEM_PROMPT.lower()
        
        assert "challenge" in prompt_lower or "risk" in prompt_lower
    
    def test_prohibits_file_modifications(self):
        """Test that prompt prohibits file modifications."""
        prompt_lower = PLAN_SYSTEM_PROMPT.lower()
        
        assert "not have access to file editing tools" in prompt_lower
        assert "cannot" in prompt_lower
        assert "must not" in prompt_lower


class TestRunPlanSubagent:
    """Tests for run_plan_subagent function."""
    
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
        """Test that run_plan_subagent returns SubagentResult."""
        from codepi.ai.provider import DoneEvent, TokenUsage
        
        async def mock_stream(*args, **kwargs):
            yield DoneEvent(usage=TokenUsage(input_tokens=10, output_tokens=5))
        
        runner._provider.stream = mock_stream
        
        result = await run_plan_subagent(runner, "Design an authentication system")
        
        assert isinstance(result, SubagentResult)
    
    @pytest.mark.asyncio
    async def test_uses_plan_config(self, runner):
        """Test that run_plan_subagent uses plan config."""
        from codepi.ai.provider import DoneEvent, TokenUsage
        
        streamed_system = None
        
        async def mock_stream(*args, **kwargs):
            nonlocal streamed_system
            streamed_system = kwargs.get("system")
            yield DoneEvent(usage=TokenUsage(input_tokens=10, output_tokens=5))
        
        runner._provider.stream = mock_stream
        
        await run_plan_subagent(runner, "Test prompt")
        
        assert streamed_system is not None
        assert "software architect" in streamed_system.lower() or "planning specialist" in streamed_system.lower()


class TestPlanReadOnlyConstraints:
    """Tests for read-only constraints in plan subagent."""
    
    def test_config_is_read_only(self):
        """Test that plan config has read_only=True."""
        config = PlanSubagentConfig.create()
        assert config.read_only is True
    
    def test_no_write_tool(self):
        """Test that write tool is not in whitelist."""
        config = PlanSubagentConfig.create()
        assert "write" not in config.tools
    
    def test_no_edit_tool(self):
        """Test that edit tool is not in whitelist."""
        config = PlanSubagentConfig.create()
        assert "edit" not in config.tools
    
    def test_bash_is_readonly_wrapped(self):
        """Test that bash tool will be wrapped for read-only mode."""
        from codepi.core.subagent import ReadOnlyBashFilter
        
        filter = ReadOnlyBashFilter()
        
        assert filter.is_allowed("ls -la")[0]
        assert filter.is_allowed("git status")[0]
        assert filter.is_allowed("find . -name '*.py'")[0]
        
        assert not filter.is_allowed("rm -rf /tmp")[0]
        assert not filter.is_allowed("mkdir test")[0]
        assert not filter.is_allowed("git add .")[0]
