from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid


@dataclass(slots=True)
class RollbackEntry:
    session_id: str
    operation_id: str
    timestamp: str
    target: str
    recovery_action: str
    status: str = "pending"

    @classmethod
    def pending(cls, session_id: str, target: str, recovery_action: str) -> "RollbackEntry":
        return cls(
            session_id=session_id,
            operation_id=uuid.uuid4().hex,
            timestamp=datetime.now(timezone.utc).isoformat(),
            target=target,
            recovery_action=recovery_action,
            status="pending",
        )


class RollbackJournal:
    def __init__(self, wal_path: str) -> None:
        self.wal_path = Path(wal_path)
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: RollbackEntry) -> None:
        payload = json.dumps(asdict(entry), ensure_ascii=False) + "\n"
        with self.wal_path.open("a", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())

    def mark_completed(self, entry: RollbackEntry) -> None:
        completed = RollbackEntry(
            session_id=entry.session_id,
            operation_id=entry.operation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            target=entry.target,
            recovery_action=entry.recovery_action,
            status="completed",
        )
        self.append(completed)

    def unfinished(self, session_id: str | None = None) -> list[RollbackEntry]:
        latest: dict[tuple[str, str], RollbackEntry] = {}
        ordered_keys: list[tuple[str, str]] = []
        for entry in self._iter_entries():
            if session_id and entry.session_id != session_id:
                continue
            key = (entry.session_id, entry.operation_id)
            if key not in latest:
                ordered_keys.append(key)
            latest[key] = entry

        unresolved: list[RollbackEntry] = []
        for key in ordered_keys:
            current = latest[key]
            if current.status != "completed":
                unresolved.append(current)
        return unresolved

    def _iter_entries(self) -> list[RollbackEntry]:
        if not self.wal_path.exists():
            return []
        entries: list[RollbackEntry] = []
        with self.wal_path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(RollbackEntry(**data))
                except (json.JSONDecodeError, TypeError, ValueError):
                    # tolerate truncated/partial line caused by crash
                    continue
        return entries
