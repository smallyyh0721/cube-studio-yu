from __future__ import annotations

from pathlib import Path

from fault_injector.rollback import RollbackEntry, RollbackJournal


def test_resume_recovery_reads_only_target_session_and_preserves_others(tmp_path: Path) -> None:
    wal_path = tmp_path / "rollback.wal"
    journal = RollbackJournal(str(wal_path))
    journal.record(RollbackEntry(session_id="resume-me", host="node-a", rollback_command="cmd-a"))
    journal.record(RollbackEntry(session_id="keep-me", host="node-b", rollback_command="cmd-b"))

    resume_entries = journal.load("resume-me")
    assert [entry.host for entry in resume_entries] == ["node-a"]

    journal.remove_session("resume-me")
    assert journal.load("resume-me") == []
    assert [entry.host for entry in journal.load("keep-me")] == ["node-b"]
