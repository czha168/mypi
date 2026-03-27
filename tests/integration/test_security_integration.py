"""Integration tests for security monitor + tool execution."""

import pytest
from unittest.mock import MagicMock
from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.core.security import SecurityMonitor, SecurityAction
from codepi.config import SecurityConfig
from codepi.tools.builtins import make_builtin_registry
from codepi.ai.provider import TokenEvent, DoneEvent, TokenUsage


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    
    async def mock_stream(*args, **kwargs):
        yield TokenEvent(text="done")
        yield DoneEvent(usage=TokenUsage(10, 5))
    
    provider.stream = mock_stream
    return provider


@pytest.fixture
def session_manager(tmp_sessions_dir):
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    return sm


class TestSecurityMonitorIntegration:
    def test_security_blocks_destructive_operations(self, mock_provider, session_manager):
        config = SecurityConfig(enabled=True)
        monitor = SecurityMonitor(config=config)
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            security_monitor=monitor,
        )
        
        decision = monitor.evaluate_tool_call(
            "bash",
            {"command": "rm -rf /important/data"}
        )
        assert decision.action == SecurityAction.BLOCK
        assert "destructive" in decision.reason.lower()

    def test_security_blocks_force_push(self, mock_provider, session_manager):
        config = SecurityConfig(enabled=True)
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_tool_call(
            "bash",
            {"command": "git push --force origin main"}
        )
        assert decision.action == SecurityAction.ASK
        assert "force" in decision.reason.lower()

    def test_security_asks_for_normal_push(self, mock_provider, session_manager):
        config = SecurityConfig(enabled=True)
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_tool_call(
            "bash",
            {"command": "git push origin main"}
        )
        assert decision.action == SecurityAction.ASK
        assert "shared" in decision.reason.lower() or "push" in decision.reason.lower()

    def test_security_asks_for_credential_files(self, mock_provider, session_manager):
        config = SecurityConfig(enabled=True)
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_tool_call(
            "read",
            {"file_path": "/project/.env"}
        )
        assert decision.action == SecurityAction.ASK
        assert "secret" in decision.reason.lower() or "credential" in decision.reason.lower()

    def test_security_allows_safe_operations(self, mock_provider, session_manager):
        config = SecurityConfig(enabled=True)
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_tool_call(
            "bash",
            {"command": "ls -la"}
        )
        assert decision.action == SecurityAction.ALLOW

    def test_security_allows_safe_reads(self, mock_provider, session_manager):
        config = SecurityConfig(enabled=True)
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_tool_call(
            "read",
            {"file_path": "/project/src/main.py"}
        )
        assert decision.action == SecurityAction.ALLOW

    def test_security_can_be_disabled(self, mock_provider, session_manager):
        config = SecurityConfig(enabled=False)
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_tool_call(
            "bash",
            {"command": "rm -rf /data"}
        )
        assert decision.action == SecurityAction.ALLOW

    def test_security_rule_overrides(self, mock_provider, session_manager):
        config = SecurityConfig(
            enabled=True,
            rule_overrides={"shared:push": "allow"}
        )
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_tool_call(
            "bash",
            {"command": "git push origin main"}
        )
        assert decision.action == SecurityAction.ALLOW


class TestToolCallWithSecurity:
    @pytest.mark.asyncio
    async def test_tool_result_includes_block_reason(self, mock_provider, session_manager):
        from codepi.tools.base import ToolRegistry, Tool, ToolResult
        
        class MockWriteTool(Tool):
            name = "write"
            description = "write"
            input_schema = {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}}
            async def execute(self, file_path="", content=""):
                return ToolResult(output=f"Wrote {file_path}")
        
        config = SecurityConfig(enabled=True)
        monitor = SecurityMonitor(config=config)
        registry = ToolRegistry()
        registry.register(MockWriteTool())
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=registry,
            security_monitor=monitor,
        )
        
        blocked, reason = session._is_edit_blocked_by_plan_mode(
            "write", {"file_path": "/tmp/test.py", "content": "test"}
        )
        
    def test_security_integration_in_session(self, mock_provider, session_manager):
        config = SecurityConfig(enabled=True)
        monitor = SecurityMonitor(config=config)
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            security_monitor=monitor,
        )
        
        decision = monitor.evaluate_tool_call("bash", {"command": "rm -rf /"})
        assert decision.action == SecurityAction.BLOCK
