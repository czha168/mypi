"""Unit tests for subagent framework."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from codepi.core.subagent import (
    SubagentConfig,
    SubagentResult,
    SubagentStatus,
    SubagentRunner,
    ReadOnlyBashFilter,
)


class TestReadOnlyBashFilter:
    """Tests for read-only bash command filtering."""
    
    def test_allows_ls(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("ls -la")
        assert allowed
        assert reason == ""
    
    def test_allows_git_status(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("git status")
        assert allowed
    
    def test_allows_git_log(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("git log --oneline -10")
        assert allowed
    
    def test_allows_git_diff(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("git diff HEAD")
        assert allowed
    
    def test_allows_cat(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("cat file.txt")
        assert allowed
    
    def test_allows_find(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("find . -name '*.py'")
        assert allowed
    
    def test_allows_grep(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("grep -r 'pattern' src/")
        assert allowed
    
    def test_blocks_rm_rf(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("rm -rf /tmp/test")
        assert not allowed
        assert "blocked" in reason.lower()
    
    def test_blocks_mkdir(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("mkdir newdir")
        assert not allowed
    
    def test_blocks_git_add(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("git add .")
        assert not allowed
    
    def test_blocks_git_commit(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("git commit -m 'test'")
        assert not allowed
    
    def test_blocks_git_push(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("git push origin main")
        assert not allowed
    
    def test_blocks_pip_install(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("pip install requests")
        assert not allowed
    
    def test_blocks_redirect_write(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("echo test > file.txt")
        assert not allowed
    
    def test_blocks_redirect_append(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("echo test >> file.txt")
        assert not allowed
    
    def test_blocks_drop_table(self):
        filter = ReadOnlyBashFilter()
        allowed, reason = filter.is_allowed("echo 'DROP TABLE users;'")
        assert not allowed


class TestSubagentConfig:
    """Tests for SubagentConfig dataclass."""
    
    def test_default_values(self):
        config = SubagentConfig(
            name="test",
            system_prompt="Test prompt",
            tools=["read"],
        )
        assert config.read_only is False
        assert config.max_turns == 10
        assert config.timeout_seconds == 300.0
    
    def test_custom_values(self):
        config = SubagentConfig(
            name="explore",
            system_prompt="Explore prompt",
            tools=["read", "find", "grep"],
            read_only=True,
            max_turns=5,
            timeout_seconds=60.0,
        )
        assert config.read_only is True
        assert config.max_turns == 5
        assert len(config.tools) == 3


class TestSubagentResult:
    """Tests for SubagentResult dataclass."""
    
    def test_default_values(self):
        result = SubagentResult(status=SubagentStatus.PENDING)
        assert result.output == ""
        assert result.error is None
        assert result.tool_calls == []
        assert result.tokens_used == 0
    
    def test_completed_result(self):
        result = SubagentResult(
            status=SubagentStatus.COMPLETED,
            output="Task completed",
            tokens_used=100,
        )
        assert result.status == SubagentStatus.COMPLETED
        assert result.output == "Task completed"
    
    def test_failed_result(self):
        result = SubagentResult(
            status=SubagentStatus.FAILED,
            error="Something went wrong",
        )
        assert result.status == SubagentStatus.FAILED
        assert result.error == "Something went wrong"


class TestSubagentRunner:
    """Tests for SubagentRunner class."""
    
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
        registry = MagicMock()
        registry.get = MagicMock(return_value=None)
        registry.to_openai_schema = MagicMock(return_value=[])
        return registry
    
    @pytest.fixture
    def runner(self, mock_provider, mock_session_manager, mock_tool_registry):
        return SubagentRunner(
            provider=mock_provider,
            session_manager=mock_session_manager,
            model="test-model",
            tool_registry=mock_tool_registry,
        )
    
    def test_create_filtered_registry(self, runner, mock_tool_registry):
        mock_tool_registry.get = MagicMock(return_value=MagicMock())
        
        config = SubagentConfig(
            name="test",
            system_prompt="Test",
            tools=["read", "find"],
        )
        
        filtered = runner._create_filtered_registry(config)
        assert filtered is not None
    
    def test_wrap_bash_readonly(self, runner):
        mock_bash = MagicMock()
        mock_bash.execute = AsyncMock(return_value=MagicMock(output="result"))
        
        wrapped = runner._wrap_bash_readonly(mock_bash)
        assert wrapped is not None


class TestSubagentStatus:
    """Tests for SubagentStatus enum."""
    
    def test_all_statuses_exist(self):
        assert SubagentStatus.PENDING.value == "pending"
        assert SubagentStatus.RUNNING.value == "running"
        assert SubagentStatus.COMPLETED.value == "completed"
        assert SubagentStatus.FAILED.value == "failed"
        assert SubagentStatus.CANCELLED.value == "cancelled"
