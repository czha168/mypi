"""Unit tests for security monitor."""

import pytest
from unittest.mock import MagicMock

from codepi.core.security import (
    SecurityMonitor,
    SecurityAction,
    SecurityDecision,
    SecurityRule,
    DESTRUCTIVE_RULES,
    HARD_TO_REVERSE_RULES,
    SHARED_STATE_RULES,
    CREDENTIAL_RULES,
)
from codepi.config import SecurityConfig


class TestSecurityDecision:
    """Tests for SecurityDecision dataclass."""
    
    def test_default_values(self):
        """Test default values for SecurityDecision."""
        decision = SecurityDecision(
            action=SecurityAction.ALLOW,
            reason="Test",
        )
        assert decision.risk_level == "low"
        assert decision.rule_id == ""
        assert decision.metadata == {}
    
    def test_all_actions(self):
        """Test all security actions exist."""
        assert SecurityAction.ALLOW.value == "allow"
        assert SecurityAction.BLOCK.value == "block"
        assert SecurityAction.ASK.value == "ask"


class TestSecurityMonitorBasics:
    """Tests for SecurityMonitor basic functionality."""
    
    def test_allows_safe_bash_command(self):
        """Test that safe bash commands are allowed."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("ls -la")
        assert decision.action == SecurityAction.ALLOW
        
        decision = monitor.evaluate_bash_command("cat file.txt")
        assert decision.action == SecurityAction.ALLOW
        
        decision = monitor.evaluate_bash_command("find . -name '*.py'")
        assert decision.action == SecurityAction.ALLOW
    
    def test_allows_safe_file_read(self):
        """Test that safe file reads are allowed."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_file_read("/path/to/src/main.py")
        assert decision.action == SecurityAction.ALLOW
    
    def test_disabled_monitor_allows_all(self):
        """Test that disabled monitor allows all operations."""
        config = SecurityConfig(enabled=False)
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_bash_command("rm -rf /")
        assert decision.action == SecurityAction.ALLOW
        assert "disabled" in decision.reason.lower()


class TestDestructiveOperations:
    """Tests for destructive operation detection."""
    
    def test_blocks_rm_rf(self):
        """Test that rm -rf is blocked."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("rm -rf /tmp/test")
        assert decision.action == SecurityAction.BLOCK
        assert "destructive" in decision.reason.lower()
    
    def test_blocks_rm_recursive(self):
        """Test that rm -r is blocked."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("rm -r folder")
        assert decision.action == SecurityAction.BLOCK
    
    def test_blocks_drop_table(self):
        """Test that DROP TABLE is blocked."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("echo 'DROP TABLE users;'")
        assert decision.action == SecurityAction.BLOCK
        assert "drop table" in decision.reason.lower()
    
    def test_blocks_delete_from(self):
        """Test that DELETE FROM is blocked."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("echo 'DELETE FROM users;'")
        assert decision.action == SecurityAction.BLOCK
    
    def test_blocks_truncate(self):
        """Test that TRUNCATE is blocked."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("echo 'TRUNCATE users;'")
        assert decision.action == SecurityAction.BLOCK
    
    def test_blocks_kill_9(self):
        """Test that kill -9 is blocked."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("kill -9 1234")
        assert decision.action == SecurityAction.BLOCK
        assert "kill" in decision.reason.lower()


class TestHardToReverseOperations:
    """Tests for hard-to-reverse operation detection."""
    
    def test_flags_force_push(self):
        """Test that force push is flagged for user approval."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("git push --force origin main")
        assert decision.action == SecurityAction.ASK
        assert "force push" in decision.reason.lower()
    
    def test_flags_force_push_short(self):
        """Test that git push -f is flagged."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("git push -f")
        assert decision.action == SecurityAction.ASK
    
    def test_flags_hard_reset(self):
        """Test that hard reset is flagged for user approval."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("git reset --hard HEAD~1")
        assert decision.action == SecurityAction.ASK
        assert "hard reset" in decision.reason.lower()
    
    def test_flags_git_clean(self):
        """Test that git clean -fd is flagged."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("git clean -fd")
        assert decision.action == SecurityAction.ASK


class TestSharedStateOperations:
    """Tests for shared state operation detection."""
    
    def test_flags_git_push(self):
        """Test that git push is flagged for user approval."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("git push origin main")
        assert decision.action == SecurityAction.ASK
        assert "push" in decision.reason.lower()
    
    def test_flags_pr_creation(self):
        """Test that PR creation is flagged."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("gh pr create --title 'Test'")
        assert decision.action == SecurityAction.ASK
        assert "pr" in decision.reason.lower()
    
    def test_flags_npm_publish(self):
        """Test that npm publish is flagged."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("npm publish")
        assert decision.action == SecurityAction.ASK
        assert "publish" in decision.reason.lower()


class TestCredentialExposure:
    """Tests for credential exposure detection."""
    
    def test_flags_env_file_read(self):
        """Test that .env file read is flagged."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_file_read(".env")
        assert decision.action == SecurityAction.ASK
        assert "secret" in decision.reason.lower() or "env" in decision.reason.lower()
    
    def test_flags_env_local_read(self):
        """Test that .env.local file read is flagged."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_file_read(".env.local")
        assert decision.action == SecurityAction.ASK
    
    def test_flags_credentials_file(self):
        """Test that credentials.json file read is flagged."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_file_read("credentials.json")
        assert decision.action == SecurityAction.ASK
    
    def test_blocks_private_key_write(self):
        """Test that writing private key content is blocked."""
        monitor = SecurityMonitor()
        
        content = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        decision = monitor.evaluate_file_write("key.pem", content)
        assert decision.action == SecurityAction.BLOCK
        assert "private key" in decision.reason.lower()
    
    def test_flags_api_key_in_content(self):
        """Test that writing API key content is flagged."""
        monitor = SecurityMonitor()
        
        content = 'api_key = "sk-1234567890abcdefghijklmnop"'
        decision = monitor.evaluate_file_write("config.py", content)
        assert decision.action == SecurityAction.ASK


class TestRuleOverrides:
    """Tests for rule configuration overrides."""
    
    def test_override_to_allow(self):
        """Test that rule can be overridden to allow."""
        config = SecurityConfig(
            enabled=True,
            rule_overrides={"shared:push": "allow"}
        )
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_bash_command("git push origin main")
        assert decision.action == SecurityAction.ALLOW
    
    def test_override_to_block(self):
        """Test that rule can be overridden to block."""
        config = SecurityConfig(
            enabled=True,
            rule_overrides={"shared:push": "block"}
        )
        monitor = SecurityMonitor(config=config)
        
        decision = monitor.evaluate_bash_command("git push origin main")
        assert decision.action == SecurityAction.BLOCK
    
    def test_runtime_override(self):
        """Test runtime rule override."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_bash_command("git push origin main")
        assert decision.action == SecurityAction.ASK
        
        monitor.add_rule_override("shared:push", SecurityAction.ALLOW)
        
        decision = monitor.evaluate_bash_command("git push origin main")
        assert decision.action == SecurityAction.ALLOW
        
        monitor.remove_rule_override("shared:push")
        
        decision = monitor.evaluate_bash_command("git push origin main")
        assert decision.action == SecurityAction.ASK


class TestToolCallEvaluation:
    """Tests for tool call evaluation."""
    
    def test_evaluates_bash_tool(self):
        """Test that bash tool is evaluated."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_tool_call("bash", {"command": "rm -rf /tmp"})
        assert decision.action == SecurityAction.BLOCK
    
    def test_evaluates_read_tool(self):
        """Test that read tool is evaluated."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_tool_call("read", {"file_path": ".env"})
        assert decision.action == SecurityAction.ASK
    
    def test_evaluates_write_tool(self):
        """Test that write tool is evaluated."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_tool_call("write", {
            "file_path": "config.py",
            "content": "api_key = 'sk-1234567890abcdef'"
        })
        assert decision.action == SecurityAction.ASK
    
    def test_allows_unknown_tool(self):
        """Test that unknown tools are allowed."""
        monitor = SecurityMonitor()
        
        decision = monitor.evaluate_tool_call("unknown_tool", {})
        assert decision.action == SecurityAction.ALLOW


class TestSecurityRules:
    """Tests for security rule definitions."""
    
    def test_destructive_rules_exist(self):
        """Test that destructive rules are defined."""
        rule_ids = [r.id for r in DESTRUCTIVE_RULES]
        assert "destructive:rm_rf" in rule_ids
        assert "destructive:drop_table" in rule_ids
        assert "destructive:kill_force" in rule_ids
    
    def test_hard_to_reverse_rules_exist(self):
        """Test that hard-to-reverse rules are defined."""
        rule_ids = [r.id for r in HARD_TO_REVERSE_RULES]
        assert "reversible:force_push" in rule_ids
        assert "reversible:hard_reset" in rule_ids
    
    def test_shared_state_rules_exist(self):
        """Test that shared state rules are defined."""
        rule_ids = [r.id for r in SHARED_STATE_RULES]
        assert "shared:push" in rule_ids
        assert "shared:pr_create" in rule_ids
    
    def test_credential_rules_exist(self):
        """Test that credential rules are defined."""
        rule_ids = [r.id for r in CREDENTIAL_RULES]
        assert "credential:env_file" in rule_ids
        assert "credential:api_key" in rule_ids
        assert "credential:private_key" in rule_ids
    
    def test_get_all_rules(self):
        """Test that get_all_rules returns all rules."""
        monitor = SecurityMonitor()
        all_rules = monitor.get_all_rules()
        
        assert len(all_rules) == len(DESTRUCTIVE_RULES) + len(HARD_TO_REVERSE_RULES) + \
               len(SHARED_STATE_RULES) + len(CREDENTIAL_RULES)
