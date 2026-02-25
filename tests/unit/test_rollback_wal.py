from __future__ import annotations

from pathlib import Path

from fault_injector.rollback import RollbackEntry, RollbackJournal


def test_wal_record_load_and_remove_session(tmp_path: Path) -> None:
    wal = RollbackJournal(str(tmp_path / "rollback.wal"))
    wal.record(RollbackEntry(session_id="s1", host="node-a", rollback_command="cmd-a"))
    wal.record(RollbackEntry(session_id="s2", host="node-b", rollback_command="cmd-b"))

    loaded = wal.load("s1")
    assert len(loaded) == 1
    assert loaded[0].host == "node-a"

    wal.remove_session("s1")
    assert wal.load("s1") == []
    assert len(wal.load("s2")) == 1
