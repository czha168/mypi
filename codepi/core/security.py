"""Security monitor for evaluating risky operations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codepi.config import SecurityConfig


class SecurityAction(Enum):
    """Security decision actions."""
    ALLOW = "allow"
    BLOCK = "block"
    ASK = "ask"


@dataclass
class SecurityDecision:
    """Result of security evaluation."""
    action: SecurityAction
    reason: str
    risk_level: str = "low"  # low, medium, high
    rule_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityRule:
    """A security rule definition."""
    id: str
    name: str
    description: str
    patterns: list[str]
    default_action: SecurityAction
    risk_level: str
    message: str


DESTRUCTIVE_RULES = [
    SecurityRule(
        id="destructive:rm_rf",
        name="Recursive Delete",
        description="Blocking recursive delete operations",
        patterns=[r"\brm\s+(-[rf]+\s+|-[a-zA-Z]*r[a-zA-Z]*\s+).*\S"],
        default_action=SecurityAction.BLOCK,
        risk_level="high",
        message="Destructive operation detected: recursive delete (rm -rf)",
    ),
    SecurityRule(
        id="destructive:drop_table",
        name="DROP TABLE",
        description="Blocking SQL DROP TABLE operations",
        patterns=[r"\bDROP\s+TABLE\b", r"\bDROP\s+TABLE\s+IF\s+EXISTS\b"],
        default_action=SecurityAction.BLOCK,
        risk_level="high",
        message="Database destructive operation detected: DROP TABLE",
    ),
    SecurityRule(
        id="destructive:delete_from",
        name="DELETE FROM",
        description="Blocking SQL DELETE operations",
        patterns=[r"\bDELETE\s+FROM\b"],
        default_action=SecurityAction.BLOCK,
        risk_level="high",
        message="Database destructive operation detected: DELETE FROM",
    ),
    SecurityRule(
        id="destructive:truncate",
        name="TRUNCATE",
        description="Blocking SQL TRUNCATE operations",
        patterns=[r"\bTRUNCATE\s+(TABLE\s+)?\w+", r"\bTRUNCATE\b"],
        default_action=SecurityAction.BLOCK,
        risk_level="high",
        message="Database destructive operation detected: TRUNCATE",
    ),
    SecurityRule(
        id="destructive:kill_force",
        name="Force Kill Process",
        description="Blocking force kill operations",
        patterns=[r"\bkill\s+-9\b", r"\bkill\s+-KILL\b"],
        default_action=SecurityAction.BLOCK,
        risk_level="high",
        message="Destructive operation detected: force kill (kill -9)",
    ),
]

HARD_TO_REVERSE_RULES = [
    SecurityRule(
        id="reversible:force_push",
        name="Force Push",
        description="Flagging force push operations",
        patterns=[r"\bgit\s+push\s+.*--force", r"\bgit\s+push\s+-f\b"],
        default_action=SecurityAction.ASK,
        risk_level="high",
        message="Force push can overwrite upstream history. Proceed?",
    ),
    SecurityRule(
        id="reversible:hard_reset",
        name="Hard Reset",
        description="Flagging hard reset operations",
        patterns=[r"\bgit\s+reset\s+.*--hard", r"\bgit\s+reset\s+--hard\b"],
        default_action=SecurityAction.ASK,
        risk_level="high",
        message="Hard reset will lose uncommitted changes. Proceed?",
    ),
    SecurityRule(
        id="reversible:clean",
        name="Git Clean",
        description="Flagging git clean operations",
        patterns=[r"\bgit\s+clean\s+.*-fd", r"\bgit\s+clean\s+-fdx?"],
        default_action=SecurityAction.ASK,
        risk_level="high",
        message="Git clean will remove untracked files. Proceed?",
    ),
]

SHARED_STATE_RULES = [
    SecurityRule(
        id="shared:push",
        name="Git Push",
        description="Flagging git push to remote",
        patterns=[r"\bgit\s+push\b(?!\s+.*--force)"],
        default_action=SecurityAction.ASK,
        risk_level="medium",
        message="Pushing to remote. Confirm?",
    ),
    SecurityRule(
        id="shared:pr_create",
        name="Create Pull Request",
        description="Flagging PR creation",
        patterns=[r"\bgh\s+pr\s+create\b", r"\bgit\s+push.*&&.*pr"],
        default_action=SecurityAction.ASK,
        risk_level="medium",
        message="Creating PR visible to team. Confirm?",
    ),
    SecurityRule(
        id="shared:publish",
        name="Publish Package",
        patterns=[r"\bnpm\s+publish\b", r"\bpip\s+upload\b", r"\bcargo\s+publish\b"],
        default_action=SecurityAction.ASK,
        risk_level="high",
        description="Flagging package publishing",
        message="Publishing package to registry. Confirm?",
    ),
]

CREDENTIAL_RULES = [
    SecurityRule(
        id="credential:env_file",
        name="Environment File Access",
        description="Flagging access to .env files",
        patterns=[r"\.env($|\s)", r"\.env\.", r"credentials?\.(json|yaml|yml|toml)"],
        default_action=SecurityAction.ASK,
        risk_level="medium",
        message="File may contain secrets. Confirm read?",
    ),
    SecurityRule(
        id="credential:api_key",
        name="API Key Pattern",
        description="Flagging potential API key exposure",
        patterns=[
            r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']',
            r'secret[_-]?key\s*=\s*["\'][^"\']{10,}["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']{10,}["\']',
        ],
        default_action=SecurityAction.ASK,
        risk_level="high",
        message="Potential credential exposure detected. Confirm?",
    ),
    SecurityRule(
        id="credential:private_key",
        name="Private Key Pattern",
        description="Flagging private key patterns",
        patterns=[
            r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
            r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----",
        ],
        default_action=SecurityAction.BLOCK,
        risk_level="high",
        message="Private key exposure detected. Operation blocked.",
    ),
]

ALL_RULES = DESTRUCTIVE_RULES + HARD_TO_REVERSE_RULES + SHARED_STATE_RULES + CREDENTIAL_RULES


class SecurityMonitor:
    """Evaluates tool calls for security risks."""
    
    def __init__(self, config: SecurityConfig | None = None):
        """Initialize security monitor.
        
        Args:
            config: Security configuration. If None, uses default settings.
        """
        self._config = config
        self._rule_overrides: dict[str, SecurityAction] = {}
    
    def _get_rule_action(self, rule: SecurityRule) -> SecurityAction:
        """Get the action for a rule, considering config and runtime overrides."""
        if rule.id in self._rule_overrides:
            return self._rule_overrides[rule.id]
        if self._config:
            override = self._config.rule_overrides.get(rule.id)
            if override:
                return SecurityAction(override)
        return rule.default_action
    
    def evaluate_bash_command(self, command: str) -> SecurityDecision:
        """Evaluate a bash command for security risks.
        
        Args:
            command: The bash command to evaluate
            
        Returns:
            SecurityDecision with action, reason, and risk level
        """
        if self._config and not self._config.enabled:
            return SecurityDecision(
                action=SecurityAction.ALLOW,
                reason="Security monitor disabled",
                risk_level="low",
            )
        
        for rule in ALL_RULES:
            for pattern in rule.patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    action = self._get_rule_action(rule)
                    return SecurityDecision(
                        action=action,
                        reason=rule.message,
                        risk_level=rule.risk_level,
                        rule_id=rule.id,
                        metadata={"rule_name": rule.name, "matched_pattern": pattern},
                    )
        
        return SecurityDecision(
            action=SecurityAction.ALLOW,
            reason="No security concerns detected",
            risk_level="low",
        )
    
    def evaluate_file_read(self, file_path: str) -> SecurityDecision:
        """Evaluate a file read operation for security risks.
        
        Args:
            file_path: The path of the file to read
            
        Returns:
            SecurityDecision with action, reason, and risk level
        """
        if self._config and not self._config.enabled:
            return SecurityDecision(
                action=SecurityAction.ALLOW,
                reason="Security monitor disabled",
                risk_level="low",
            )
        
        for rule in CREDENTIAL_RULES:
            for pattern in rule.patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    action = self._get_rule_action(rule)
                    return SecurityDecision(
                        action=action,
                        reason=rule.message,
                        risk_level=rule.risk_level,
                        rule_id=rule.id,
                        metadata={"rule_name": rule.name, "file_path": file_path},
                    )
        
        return SecurityDecision(
            action=SecurityAction.ALLOW,
            reason="No security concerns detected",
            risk_level="low",
        )
    
    def evaluate_file_write(self, file_path: str, content: str = "") -> SecurityDecision:
        """Evaluate a file write operation for security risks.
        
        Args:
            file_path: The path of the file to write
            content: The content to write (optional, for content analysis)
            
        Returns:
            SecurityDecision with action, reason, and risk level
        """
        if self._config and not self._config.enabled:
            return SecurityDecision(
                action=SecurityAction.ALLOW,
                reason="Security monitor disabled",
                risk_level="low",
            )
        
        for rule in CREDENTIAL_RULES:
            for pattern in rule.patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    action = self._get_rule_action(rule)
                    return SecurityDecision(
                        action=action,
                        reason=rule.message,
                        risk_level=rule.risk_level,
                        rule_id=rule.id,
                        metadata={"rule_name": rule.name, "file_path": file_path},
                    )
        
        return SecurityDecision(
            action=SecurityAction.ALLOW,
            reason="No security concerns detected",
            risk_level="low",
        )
    
    def evaluate_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> SecurityDecision:
        """Evaluate a tool call for security risks.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments
            
        Returns:
            SecurityDecision with action, reason, and risk level
        """
        if self._config and not self._config.enabled:
            return SecurityDecision(
                action=SecurityAction.ALLOW,
                reason="Security monitor disabled",
                risk_level="low",
            )
        
        if tool_name == "bash":
            command = arguments.get("command", "")
            return self.evaluate_bash_command(command)
        
        if tool_name == "read":
            file_path = arguments.get("file_path", arguments.get("path", ""))
            return self.evaluate_file_read(file_path)
        
        if tool_name in ("write", "edit"):
            file_path = arguments.get("file_path", arguments.get("path", ""))
            content = arguments.get("content", arguments.get("new_string", ""))
            return self.evaluate_file_write(file_path, content)
        
        return SecurityDecision(
            action=SecurityAction.ALLOW,
            reason="Tool not subject to security checks",
            risk_level="low",
        )
    
    def add_rule_override(self, rule_id: str, action: SecurityAction) -> None:
        """Add an override for a specific rule.
        
        Args:
            rule_id: The rule ID to override
            action: The action to use instead of default
        """
        self._rule_overrides[rule_id] = action
    
    def remove_rule_override(self, rule_id: str) -> None:
        """Remove a rule override.
        
        Args:
            rule_id: The rule ID to remove override for
        """
        self._rule_overrides.pop(rule_id, None)
    
    def get_all_rules(self) -> list[SecurityRule]:
        """Get all security rules."""
        return ALL_RULES.copy()
