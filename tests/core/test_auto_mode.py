"""Unit tests for auto mode functionality."""

import pytest
from codepi.core.modes.auto_mode import (
    AutoModeState,
    AutoModeConfig,
    AutoModeContext,
    AutoModeManager,
    get_sensitive_operation_from_command,
)


class TestAutoModeConfig:
    def test_default_config(self):
        config = AutoModeConfig()
        assert not config.enabled
        assert config.max_iterations == 100
        assert "push" in config.require_approval_for
        assert "pr" in config.require_approval_for

    def test_custom_config(self):
        config = AutoModeConfig(
            enabled=True,
            max_iterations=50,
            require_approval_for=["push"],
        )
        assert config.enabled
        assert config.max_iterations == 50
        assert config.require_approval_for == ["push"]

    def test_invalid_max_iterations(self):
        config = AutoModeConfig(max_iterations=0)
        assert config.max_iterations == 100  # Reset to default

    def test_empty_require_approval_for(self):
        config = AutoModeConfig(require_approval_for=[])
        assert "push" in config.require_approval_for  # Reset to default


class TestAutoModeContext:
    def test_initial_context(self):
        ctx = AutoModeContext()
        assert ctx.iteration_count == 0
        assert ctx.tools_used == []
        assert ctx.files_modified == []
        assert ctx.errors_encountered == 0
        assert ctx.state == AutoModeState.DISABLED

    def test_increment_iteration(self):
        ctx = AutoModeContext(state=AutoModeState.ACTIVE)
        assert ctx.increment_iteration(10)
        assert ctx.iteration_count == 1
        for _ in range(8):
            ctx.increment_iteration(10)
        assert ctx.iteration_count == 9
        assert not ctx.increment_iteration(10)  # 10th fails
        assert ctx.iteration_count == 10

    def test_record_tool_use(self):
        ctx = AutoModeContext()
        ctx.record_tool_use("read")
        ctx.record_tool_use("write")
        assert "read" in ctx.tools_used
        assert "write" in ctx.tools_used

    def test_record_file_modification(self):
        ctx = AutoModeContext()
        ctx.record_file_modification("/a/file.py")
        ctx.record_file_modification("/a/file.py")  # Duplicate
        assert len(ctx.files_modified) == 1
        ctx.record_file_modification("/b/file.py")
        assert len(ctx.files_modified) == 2

    def test_record_error(self):
        ctx = AutoModeContext()
        ctx.record_error()
        ctx.record_error()
        assert ctx.errors_encountered == 2

    def test_serialization(self):
        ctx = AutoModeContext(
            iteration_count=5,
            tools_used=["read", "write"],
            files_modified=["/a.py"],
            errors_encountered=1,
            approvals_requested=2,
            state=AutoModeState.ACTIVE,
        )
        data = ctx.to_dict()
        assert data["iteration_count"] == 5
        assert data["tools_used"] == ["read", "write"]
        assert data["state"] == "active"


class TestAutoModeManager:
    def test_is_active_when_disabled(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=False))
        assert not manager.is_active

    def test_is_active_when_enabled(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        assert manager.is_active

    def test_start(self):
        manager = AutoModeManager()
        manager.start()
        assert manager.is_active
        assert manager.context.iteration_count == 0

    def test_stop(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        manager.context.iteration_count = 5
        final = manager.stop()
        assert not manager.is_active
        assert final.iteration_count == 5

    def test_pause_and_resume(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        manager.pause("test")
        assert manager.is_paused
        manager.resume()
        assert manager.is_active

    def test_check_iteration_limit(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True, max_iterations=3))
        can_continue, _ = manager.check_iteration_limit()
        assert can_continue
        can_continue, _ = manager.check_iteration_limit()
        assert can_continue
        can_continue, msg = manager.check_iteration_limit()
        assert not can_continue
        assert "limit" in msg.lower()

    def test_requires_approval_for_push(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        assert manager.requires_approval("push", "bash", {"command": "git push"})

    def test_requires_approval_for_pr(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        assert manager.requires_approval("pr", "bash", {"command": "gh pr create"})

    def test_requires_approval_for_non_sensitive(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        assert not manager.requires_approval("read", "read", {"file_path": "/tmp/x"})

    def test_requires_approval_detects_git_push_in_bash(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True, require_approval_for=["push"]))
        assert manager.requires_approval("", "bash", {"command": "git push origin main"})

    def test_check_and_request_approval_allows_non_sensitive(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        approved, _ = manager.check_and_request_approval("read", "read", {})
        assert approved

    def test_check_and_request_approval_blocks_sensitive(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        approved, msg = manager.check_and_request_approval("push", "bash", {"command": "git push"})
        assert not approved
        assert "approval" in msg.lower() or "push" in msg.lower()

    def test_check_and_request_approval_with_callback(self):
        approvals = []
        manager = AutoModeManager(
            config=AutoModeConfig(enabled=True),
            on_approval_needed=lambda reason, op: (approvals.append((reason, op)), True)[-1],
        )
        approved, _ = manager.check_and_request_approval("push", "bash", {"command": "git push"})
        assert approved
        assert len(approvals) == 1

    def test_get_prompt_context(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True, max_iterations=50))
        ctx = manager.get_prompt_context()
        assert ctx["auto_mode_active"]
        assert ctx["max_iterations"] == 50

    def test_get_auto_mode_directive(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=True))
        directive = manager.get_auto_mode_directive()
        assert "Auto Mode" in directive
        assert "Execute immediately" in directive

    def test_get_auto_mode_directive_when_disabled(self):
        manager = AutoModeManager(config=AutoModeConfig(enabled=False))
        assert manager.get_auto_mode_directive() == ""


class TestGetSensitiveOperationFromCommand:
    def test_git_push(self):
        assert get_sensitive_operation_from_command("git push origin main") == "push"

    def test_git_force_push(self):
        assert get_sensitive_operation_from_command("git push --force") == "force_push"

    def test_git_push_f(self):
        assert get_sensitive_operation_from_command("git push -f origin") == "force_push"

    def test_gh_pr_create(self):
        assert get_sensitive_operation_from_command("gh pr create --title 'x'") == "pr"

    def test_gh_pr_merge(self):
        assert get_sensitive_operation_from_command("gh pr merge 123") == "pr"

    def test_npm_publish(self):
        assert get_sensitive_operation_from_command("npm publish") == "publish"

    def test_twine_upload(self):
        assert get_sensitive_operation_from_command("twine upload dist/*") == "publish"

    def test_kubectl_apply(self):
        assert get_sensitive_operation_from_command("kubectl apply -f deploy.yaml") == "deploy"

    def test_terraform_apply(self):
        assert get_sensitive_operation_from_command("terraform apply") == "deploy"

    def test_non_sensitive_command(self):
        assert get_sensitive_operation_from_command("ls -la") is None

    def test_git_status(self):
        assert get_sensitive_operation_from_command("git status") is None

    def test_read_file(self):
        assert get_sensitive_operation_from_command("cat file.txt") is None
