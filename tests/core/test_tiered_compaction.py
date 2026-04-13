from codepi.core.agent_session import parse_tiered_response
from codepi.core.session_manager import SessionManager, SessionEntry


class TestParseTieredResponse:
    def test_valid_structured(self):
        raw = "ABSTRACT:\ntest abstract keywords\n\nOVERVIEW:\ntest overview content here"
        l0, l1 = parse_tiered_response(raw)
        assert l0 == "test abstract keywords"
        assert l1 == "test overview content here"

    def test_malformed_fallback(self):
        raw = "This is just a plain paragraph with no structure at all."
        l0, l1 = parse_tiered_response(raw)
        assert l1 == raw.strip()
        assert len(l0) > 0

    def test_case_insensitive_headers(self):
        raw = "abstract:\nkeywords\n\noverview:\ncontent"
        l0, l1 = parse_tiered_response(raw)
        assert l0 == "keywords"
        assert l1 == "content"


class TestBuildContextTieredCompaction:
    def test_tiered_compaction_uses_l1(self, tmp_path):
        sm = SessionManager(sessions_dir=tmp_path / "sessions")
        sm.new_session(model="test")
        sm.append(SessionEntry(
            type="message", data={"role": "user", "content": "hello"},
        ))
        sm.append(SessionEntry(
            type="tiered_compaction",
            data={"l0": "keywords", "l1": "overview content", "summary": "overview content"},
        ))
        sm.append(SessionEntry(
            type="message", data={"role": "user", "content": "after compaction"},
        ))
        context = sm.build_context()
        assert any("overview content" in m.get("content", "") for m in context)
        assert any("after compaction" in m.get("content", "") for m in context)

    def test_old_compaction_backward_compat(self, tmp_path):
        sm = SessionManager(sessions_dir=tmp_path / "sessions")
        sm.new_session(model="test")
        sm.append(SessionEntry(
            type="message", data={"role": "user", "content": "hello"},
        ))
        sm.append(SessionEntry(
            type="compaction", data={"summary": "flat summary text"},
        ))
        sm.append(SessionEntry(
            type="message", data={"role": "user", "content": "after compaction"},
        ))
        context = sm.build_context()
        assert any("flat summary text" in m.get("content", "") for m in context)
        assert any("after compaction" in m.get("content", "") for m in context)
