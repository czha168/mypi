from codepi.core.events import (
    BeforeAgentStartEvent, BeforeProviderRequestEvent,
    ToolCallEvent, ToolResultEvent,
    SessionForkEvent, SessionTreeEvent,
    AutoCompactionStartEvent, AutoCompactionEndEvent,
    AutoRetryStartEvent, AutoRetryEndEvent,
)
from codepi.tools.base import ToolResult


def test_before_agent_start_event_is_mutable():
    evt = BeforeAgentStartEvent(system_prompt="hello", messages=[])
    evt2 = BeforeAgentStartEvent(system_prompt="modified", messages=[{"role": "user", "content": "hi"}])
    assert evt.system_prompt == "hello"
    assert evt2.system_prompt == "modified"


def test_tool_call_event_fields():
    evt = ToolCallEvent(tool_name="read", arguments={"path": "foo.py"})
    assert evt.tool_name == "read"
    assert evt.arguments == {"path": "foo.py"}


def test_tool_result_event_fields():
    result = ToolResult(output="file contents")
    evt = ToolResultEvent(tool_name="read", result=result)
    assert evt.result.output == "file contents"


def test_notification_events():
    fork = SessionForkEvent(from_entry_id="a", new_entry_id="b")
    tree = SessionTreeEvent(leaf_id="c")
    compaction_start = AutoCompactionStartEvent()
    compaction_end = AutoCompactionEndEvent(summary="summarized 10 messages")
    retry_start = AutoRetryStartEvent(attempt=1)
    retry_end = AutoRetryEndEvent(attempt=1)
    assert fork.from_entry_id == "a"
    assert tree.leaf_id == "c"
    assert compaction_end.summary == "summarized 10 messages"
    assert retry_start.attempt == 1
