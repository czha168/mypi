"""Integration tests for mode switching behavior."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.core.modes.plan_mode import PlanModeManager, PlanModeConfig, PlanPhase
from codepi.core.modes.auto_mode import AutoModeManager, AutoModeConfig
from codepi.tools.builtins import make_builtin_registry


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    
    async def mock_stream(*args, **kwargs):
        from codepi.ai.provider import TokenEvent, DoneEvent, TokenUsage
        yield TokenEvent(text="done")
        yield DoneEvent(usage=TokenUsage(10, 5))
    
    provider.stream = mock_stream
    return provider


@pytest.fixture
def session_manager(tmp_sessions_dir):
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    return sm


class TestPlanModeSwitching:
    def test_plan_mode_blocks_edits(self, mock_provider, session_manager):
        plan_manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            plan_mode_manager=plan_manager,
        )
        
        blocked, reason = session._is_edit_blocked_by_plan_mode(
            "write", {"file_path": "/tmp/test.py"}
        )
        assert blocked
        assert "Plan mode active" in reason

    def test_plan_mode_allows_plan_file_edits(self, mock_provider, session_manager, tmp_path):
        from pathlib import Path
        plan_file = tmp_path / "plan.md"
        plan_manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        plan_manager.start("Test request", plan_file=plan_file)
        assert plan_manager.state is not None
        plan_manager.state.phase = PlanPhase.FINALIZE
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            plan_mode_manager=plan_manager,
        )
        
        blocked, _ = session._is_edit_blocked_by_plan_mode(
            "write", {"file_path": str(plan_file)}
        )
        assert not blocked

    def test_plan_mode_non_edit_tools_not_blocked(self, mock_provider, session_manager):
        plan_manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            plan_mode_manager=plan_manager,
        )
        
        blocked, _ = session._is_edit_blocked_by_plan_mode(
            "read", {"file_path": "/tmp/test.py"}
        )
        assert not blocked

    def test_start_plan_mode(self, mock_provider, session_manager):
        mode_changes = []
        
        def track_mode_change(old, new):
            mode_changes.append((old, new))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            on_mode_change=track_mode_change,
        )
        
        session.start_plan_mode("Test request")
        
        assert session.current_mode == "plan"
        assert ("normal", "plan") in mode_changes

    def test_stop_plan_mode(self, mock_provider, session_manager):
        mode_changes = []
        
        def track_mode_change(old, new):
            mode_changes.append((old, new))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            on_mode_change=track_mode_change,
        )
        
        session.start_plan_mode("Test")
        session.stop_plan_mode()
        
        assert session.current_mode == "normal"
        assert ("plan", "normal") in mode_changes


class TestAutoModeSwitching:
    def test_start_auto_mode(self, mock_provider, session_manager):
        mode_changes = []
        
        def track_mode_change(old, new):
            mode_changes.append((old, new))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            on_mode_change=track_mode_change,
        )
        
        session.start_auto_mode()
        
        assert session.current_mode == "auto"
        assert ("normal", "auto") in mode_changes

    def test_stop_auto_mode(self, mock_provider, session_manager):
        mode_changes = []
        
        def track_mode_change(old, new):
            mode_changes.append((old, new))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            on_mode_change=track_mode_change,
        )
        
        session.start_auto_mode()
        session.stop_auto_mode()
        
        assert session.current_mode == "normal"
        assert ("auto", "normal") in mode_changes

    def test_auto_mode_iteration_limit(self, mock_provider, session_manager):
        auto_manager = AutoModeManager(config=AutoModeConfig(enabled=True, max_iterations=2))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            auto_mode_manager=auto_manager,
        )
        
        can_continue, msg1 = auto_manager.check_iteration_limit()
        assert can_continue
        
        can_continue, msg2 = auto_manager.check_iteration_limit()
        assert not can_continue
        assert "limit" in msg2.lower()

    def test_auto_mode_approval_gate(self, mock_provider, session_manager):
        approvals = []
        
        def track_approval(reason, operation):
            approvals.append((reason, operation))
            return False
        
        auto_manager = AutoModeManager(
            config=AutoModeConfig(enabled=True),
            on_approval_needed=track_approval,
        )
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            auto_mode_manager=auto_manager,
        )
        
        approved, msg = auto_manager.check_and_request_approval(
            "push", "bash", {"command": "git push"}
        )
        assert not approved
        assert len(approvals) == 1


class TestModeCurrentModeProperty:
    def test_current_mode_normal_by_default(self, mock_provider, session_manager):
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
        )
        
        assert session.current_mode == "normal"
        assert session.plan_phase is None

    def test_current_mode_returns_plan_when_active(self, mock_provider, session_manager):
        plan_manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            plan_mode_manager=plan_manager,
        )
        
        assert session.current_mode == "plan"
        assert session.plan_phase == 1

    def test_current_mode_returns_auto_when_active(self, mock_provider, session_manager):
        auto_manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        
        session = AgentSession(
            provider=mock_provider,
            session_manager=session_manager,
            model="gpt-4o",
            tool_registry=make_builtin_registry(),
            auto_mode_manager=auto_manager,
        )
        
        assert session.current_mode == "auto"
