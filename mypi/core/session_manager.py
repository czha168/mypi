from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SessionEntry:
    type: str
    data: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None

    def to_jsonl(self) -> str:
        return json.dumps({"id": self.id, "parentId": self.parent_id,
                           "type": self.type, **self.data})

    @classmethod
    def from_dict(cls, d: dict) -> SessionEntry:
        d = dict(d)  # don't mutate caller's dict
        entry_id = d.pop("id", None) or str(uuid.uuid4())
        parent_id = d.pop("parentId", None)
        entry_type = d.pop("type")
        return cls(id=entry_id, parent_id=parent_id, type=entry_type, data=d)


class SessionManager:
    VERSION = 3

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._session_id: str | None = None
        self._session_file: Path | None = None
        self._entries: list[SessionEntry] = []
        self._active_leaf_id: str | None = None

    def new_session(self, model: str) -> str:
        self._session_id = str(uuid.uuid4())
        self._session_file = self.sessions_dir / f"{self._session_id}.jsonl"
        self._entries = []
        self._active_leaf_id = None
        root = SessionEntry(
            type="session_info",
            data={"version": self.VERSION, "model": model, "created_at": self._now()},
        )
        self._write_entry(root)
        return self._session_id

    def load_session(self, session_id: str) -> None:
        self._session_id = session_id
        self._session_file = self.sessions_dir / f"{session_id}.jsonl"
        self._entries = []
        with self._session_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    d = json.loads(line)
                    self._entries.append(SessionEntry.from_dict(d))
        self._migrate_if_needed()
        leaf_ids = self.get_leaf_ids()
        self._active_leaf_id = leaf_ids[-1] if leaf_ids else (self._entries[-1].id if self._entries else None)

    def append(self, entry: SessionEntry) -> SessionEntry:
        """Append entry as a child of the current active leaf.

        Note: entry.parent_id is always set to the current active leaf id,
        overwriting any parent_id the caller may have set.
        """
        entry.parent_id = self._active_leaf_id
        self._write_entry(entry)
        return entry

    def branch(self, from_entry_id: str) -> str:
        """Create new branch rooted at from_entry_id. Returns new active leaf id."""
        self._active_leaf_id = from_entry_id
        return from_entry_id

    def set_active_leaf(self, entry_id: str) -> None:
        self._active_leaf_id = entry_id

    def get_leaf_ids(self) -> list[str]:
        """Return all entry ids that have no children."""
        parent_ids = {e.parent_id for e in self._entries if e.parent_id}
        return [e.id for e in self._entries if e.id not in parent_ids]

    @property
    def current_leaf_id(self) -> str | None:
        return self._active_leaf_id

    def load_all_entries(self) -> list[SessionEntry]:
        return list(self._entries)

    def build_context(self, leaf_id: str | None = None) -> list[dict]:
        """Walk parent chain root→leaf. At CompactionEntry, discard prior messages (path-local)."""
        leaf_id = leaf_id or self._active_leaf_id
        if not leaf_id:
            return []

        by_id = {e.id: e for e in self._entries}
        path: list[SessionEntry] = []
        current_id: str | None = leaf_id
        while current_id:
            entry = by_id.get(current_id)
            if entry is None:
                break
            path.append(entry)
            current_id = entry.parent_id
        path.reverse()  # root → leaf

        messages: list[dict] = []
        for entry in path:
            if entry.type == "session_info":
                continue
            if entry.type == "compaction":
                # Path-local: reset messages, inject summary
                messages = [{"role": "system", "content": f"[Context summary]: {entry.data.get('summary', '')}"}]
            elif entry.type == "message":
                role = entry.data.get("role", "user")
                content = entry.data.get("content", "")
                if role == "tool":
                    # Tool messages require tool_call_id and name fields
                    messages.append({
                        "role": role,
                        "tool_call_id": entry.data.get("tool_call_id"),
                        "name": entry.data.get("name"),
                        "content": content,
                    })
                elif role == "assistant":
                    # Assistant messages with tool_calls need to preserve that field
                    msg = {"role": role, "content": content}
                    if "tool_calls" in entry.data:
                        msg["tool_calls"] = entry.data["tool_calls"]
                    messages.append(msg)
                else:
                    messages.append({"role": role, "content": content})
        return messages

    @staticmethod
    def list_sessions(sessions_dir: Path) -> list[str]:
        return [p.stem for p in Path(sessions_dir).glob("*.jsonl")]

    def _write_entry(self, entry: SessionEntry) -> None:
        self._entries.append(entry)
        self._active_leaf_id = entry.id
        with self._session_file.open("a") as f:
            f.write(entry.to_jsonl() + "\n")

    def _migrate_if_needed(self) -> None:
        if not self._entries:
            return
        first = self._entries[0]
        if first.data.get("version", 1) < 2:
            self._migrate_v1_to_v2()
        if first.data.get("version", 1) < 3:
            self._migrate_v2_to_v3()

    def _migrate_v1_to_v2(self) -> None:
        """Add id/parentId tree structure."""
        prev_id = None
        for entry in self._entries:
            if not entry.id:
                entry.id = str(uuid.uuid4())
            entry.parent_id = prev_id
            prev_id = entry.id
        if self._entries:
            self._entries[0].data["version"] = 2
        self._rewrite_file()

    def _migrate_v2_to_v3(self) -> None:
        """Rename hookMessage → custom."""
        for entry in self._entries:
            if entry.type == "hookMessage":
                entry.type = "custom"
        if self._entries:
            self._entries[0].data["version"] = 3
        self._rewrite_file()

    def _rewrite_file(self) -> None:
        with self._session_file.open("w") as f:
            for entry in self._entries:
                f.write(entry.to_jsonl() + "\n")

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
