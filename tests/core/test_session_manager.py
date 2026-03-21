import json
import pytest
from pathlib import Path
from mypi.core.session_manager import SessionManager, SessionEntry


def test_append_creates_jsonl_file(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    session_id = sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "hello"}))
    path = tmp_sessions_dir / f"{session_id}.jsonl"
    assert path.exists()
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2  # session_info + message


def test_parent_id_chains_correctly(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "a"}))
    sm.append(SessionEntry(type="message", data={"role": "assistant", "content": "b"}))
    entries = sm.load_all_entries()
    assert entries[1].parent_id == entries[0].id
    assert entries[2].parent_id == entries[1].id


def test_branch_creates_new_leaf(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "a"}))
    entry_a = sm.current_leaf_id
    sm.append(SessionEntry(type="message", data={"role": "assistant", "content": "b"}))

    sm.branch(entry_a)  # type: ignore[reportArgumentType]
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "branch msg"}))

    leaf_ids = sm.get_leaf_ids()
    assert len(leaf_ids) == 2


def test_list_sessions(tmp_sessions_dir):
    sm1 = SessionManager(sessions_dir=tmp_sessions_dir)
    sm1.new_session(model="gpt-4o")
    sm2 = SessionManager(sessions_dir=tmp_sessions_dir)
    sm2.new_session(model="gpt-4o")
    sessions = SessionManager.list_sessions(tmp_sessions_dir)
    assert len(sessions) == 2


def test_build_context_returns_messages_in_order(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "hello"}))
    sm.append(SessionEntry(type="message", data={"role": "assistant", "content": "world"}))
    ctx = sm.build_context()
    assert ctx == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    ]


def test_build_context_truncates_at_compaction(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "old message"}))
    sm.append(SessionEntry(type="compaction", data={"summary": "user said old message"}))
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "new message"}))
    ctx = sm.build_context()
    assert not any(m.get("content") == "old message" for m in ctx)
    assert any("user said old message" in m.get("content", "") for m in ctx)
    assert any(m.get("content") == "new message" for m in ctx)


def test_compaction_is_path_local(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "shared"}))
    branch_point = sm.current_leaf_id

    # Main branch: add compaction
    sm.append(SessionEntry(type="compaction", data={"summary": "main branch compacted"}))
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "main continued"}))

    # Switch to side branch from before compaction
    sm.branch(branch_point)  # type: ignore[reportArgumentType]
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "side branch"}))
    side_leaf = sm.current_leaf_id

    # Side branch context should NOT be affected by main branch compaction
    side_ctx = sm.build_context(side_leaf)
    assert any(m.get("content") == "shared" for m in side_ctx)
    assert any(m.get("content") == "side branch" for m in side_ctx)
    assert not any("compacted" in m.get("content", "") for m in side_ctx)


def test_migrate_v1_to_v3(tmp_sessions_dir):
    """A v1 file (flat, no id/parentId) should be migrated to v3 on load."""
    session_id = "test-v1-session"
    v1_file = tmp_sessions_dir / f"{session_id}.jsonl"
    v1_file.write_text(
        json.dumps({"type": "session_info", "version": 1, "model": "gpt-3.5"}) + "\n" +
        json.dumps({"type": "hookMessage", "extension": "foo", "data": {}}) + "\n"
    )
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.load_session(session_id)
    entries = sm.load_all_entries()
    assert entries[0].data.get("version") == 3
    assert entries[1].type == "custom"  # hookMessage → custom
    assert entries[0].id is not None
    assert entries[1].parent_id == entries[0].id
