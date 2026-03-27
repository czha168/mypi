"""Unit tests for plan mode functionality."""

import pytest
from pathlib import Path
from codepi.core.modes.plan_mode import (
    PlanPhase,
    PlanModeState,
    PlanModeConfig,
    PlanModeManager,
    PHASE_NAMES,
)


class TestPlanPhase:
    def test_phase_order(self):
        assert PlanPhase.UNDERSTAND.value == 1
        assert PlanPhase.DESIGN.value == 2
        assert PlanPhase.REVIEW.value == 3
        assert PlanPhase.FINALIZE.value == 4
        assert PlanPhase.EXIT.value == 5

    def test_phase_next(self):
        assert PlanPhase.UNDERSTAND.next() == PlanPhase.DESIGN
        assert PlanPhase.DESIGN.next() == PlanPhase.REVIEW
        assert PlanPhase.REVIEW.next() == PlanPhase.FINALIZE
        assert PlanPhase.FINALIZE.next() == PlanPhase.EXIT
        assert PlanPhase.EXIT.next() == PlanPhase.EXIT

    def test_phase_prev(self):
        assert PlanPhase.EXIT.prev() == PlanPhase.FINALIZE
        assert PlanPhase.FINALIZE.prev() == PlanPhase.REVIEW
        assert PlanPhase.REVIEW.prev() == PlanPhase.DESIGN
        assert PlanPhase.DESIGN.prev() == PlanPhase.UNDERSTAND
        assert PlanPhase.UNDERSTAND.prev() == PlanPhase.UNDERSTAND

    def test_from_int(self):
        assert PlanPhase.from_int(1) == PlanPhase.UNDERSTAND
        assert PlanPhase.from_int(5) == PlanPhase.EXIT
        assert PlanPhase.from_int(99) == PlanPhase.UNDERSTAND


class TestPlanModeState:
    def test_initial_state(self):
        state = PlanModeState()
        assert state.phase == PlanPhase.UNDERSTAND
        assert state.plan_file is None
        assert state.exploration_results == []
        assert state.design_content is None

    def test_is_edit_allowed_in_understand(self):
        state = PlanModeState(phase=PlanPhase.UNDERSTAND)
        assert not state.is_edit_allowed("/some/file.py")
        assert not state.is_edit_allowed()

    def test_is_edit_allowed_in_design(self):
        state = PlanModeState(phase=PlanPhase.DESIGN)
        assert not state.is_edit_allowed("/some/file.py")

    def test_is_edit_allowed_in_finalize_with_plan_file(self):
        plan_file = Path("/tmp/plan.md")
        state = PlanModeState(phase=PlanPhase.FINALIZE, plan_file=plan_file)
        assert state.is_edit_allowed(plan_file)
        assert not state.is_edit_allowed("/other/file.py")

    def test_is_edit_allowed_in_exit(self):
        state = PlanModeState(phase=PlanPhase.EXIT)
        assert not state.is_edit_allowed("/some/file.py")

    def test_can_advance_from_understand_without_results(self):
        state = PlanModeState(phase=PlanPhase.UNDERSTAND)
        can_advance, reason = state.can_advance()
        assert not can_advance
        assert "Exploration not complete" in reason

    def test_can_advance_from_understand_with_results(self):
        state = PlanModeState(phase=PlanPhase.UNDERSTAND, exploration_results=["found X"])
        can_advance, reason = state.can_advance()
        assert can_advance

    def test_can_advance_from_design_without_content(self):
        state = PlanModeState(phase=PlanPhase.DESIGN)
        can_advance, reason = state.can_advance()
        assert not can_advance
        assert "Design not complete" in reason

    def test_can_advance_from_design_with_content(self):
        state = PlanModeState(phase=PlanPhase.DESIGN, design_content="# Plan")
        can_advance, reason = state.can_advance()
        assert can_advance

    def test_can_advance_from_review_requires_approval(self):
        state = PlanModeState(phase=PlanPhase.REVIEW)
        can_advance, reason = state.can_advance()
        assert not can_advance
        assert "approval" in reason.lower()

    def test_advance(self):
        state = PlanModeState(phase=PlanPhase.UNDERSTAND, exploration_results=["x"])
        result = state.advance()
        assert result
        assert state.phase == PlanPhase.DESIGN

    def test_reject_and_return(self):
        state = PlanModeState(phase=PlanPhase.REVIEW, design_content="Plan")
        state.reject_and_return()
        assert state.phase == PlanPhase.DESIGN
        assert state.iteration_count == 1

    def test_get_plan_filename_default(self, tmp_path):
        state = PlanModeState()
        filename = state.get_plan_filename(tmp_path)
        assert filename.parent.name == "plans"
        assert filename.parent.parent.name == ".codepi"
        assert "plan-" in filename.name

    def test_get_plan_filename_custom(self):
        custom = Path("/custom/plan.md")
        state = PlanModeState(plan_file=custom)
        assert state.get_plan_filename() == custom

    def test_serialization(self):
        state = PlanModeState(
            phase=PlanPhase.DESIGN,
            exploration_results=["x", "y"],
            design_content="Plan content",
            user_request="Test request",
            iteration_count=2,
        )
        data = state.to_dict()
        restored = PlanModeState.from_dict(data)
        assert restored.phase == PlanPhase.DESIGN
        assert restored.exploration_results == ["x", "y"]
        assert restored.design_content == "Plan content"
        assert restored.user_request == "Test request"
        assert restored.iteration_count == 2


class TestPlanModeConfig:
    def test_default_config(self):
        config = PlanModeConfig()
        assert not config.enabled
        assert not config.auto_advance
        assert config.require_explicit_approval

    def test_string_path_conversion(self):
        config = PlanModeConfig(default_plan_dir=Path("/tmp/plans"))
        assert isinstance(config.default_plan_dir, Path)


class TestPlanModeManager:
    def test_is_active_when_disabled(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=False))
        assert not manager.is_active

    def test_is_active_when_enabled(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        assert manager.is_active

    def test_start(self):
        manager = PlanModeManager()
        manager.start("Test request")
        assert manager.is_active
        assert manager.state is not None
        assert manager.state.user_request == "Test request"
        assert manager.state.phase == PlanPhase.UNDERSTAND

    def test_stop(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        manager.start("Test")
        final_state = manager.stop()
        assert not manager.is_active
        assert final_state is not None
        assert final_state.user_request == "Test"

    def test_add_exploration_result(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        assert manager.state is not None
        manager.add_exploration_result("Found X")
        assert "Found X" in manager.state.exploration_results

    def test_set_design_content(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        assert manager.state is not None
        manager.set_design_content("Design content")
        assert manager.state.design_content == "Design content"

    def test_try_advance_blocked_without_results(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        success, msg = manager.try_advance()
        assert not success
        assert "Exploration" in msg

    def test_try_advance_succeeds_with_results(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        manager.add_exploration_result("Result")
        success, msg = manager.try_advance()
        assert success
        assert manager.state is not None
        assert manager.state.phase == PlanPhase.DESIGN

    def test_get_phase_prompt_context(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        ctx = manager.get_phase_prompt_context()
        assert ctx["plan_mode_active"]
        assert ctx["phase"] == 1
        assert ctx["phase_name"] == "UNDERSTAND"

    def test_get_phase_directive(self):
        manager = PlanModeManager(config=PlanModeConfig(enabled=True))
        directive = manager.get_phase_directive()
        assert "UNDERSTAND" in directive
        assert "explore" in directive.lower()
