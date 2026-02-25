from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from channel.ssh import HostSpec, SSHChannel
from fault_injector.config import InjectorConfig
from fault_injector.safety.guard import SafetyGuard
from fault_injector.safety.rollback import RollbackEntry, RollbackJournal


@dataclass(slots=True)
class RollbackReport:
    host: str
    rollback_command: str
    success: bool


class SessionWatchdog:
    def __init__(
        self,
        timeout_seconds: int,
        config: InjectorConfig,
        journal: RollbackJournal,
        channel: SSHChannel,
        guard: SafetyGuard,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.config = config
        self.journal = journal
        self.channel = channel
        self.guard = guard

    def trigger_timeout_rollback(self, session_id: str, started_at: datetime, now: datetime | None = None) -> list[RollbackReport]:
        current_time = now or datetime.now(timezone.utc)
        if (current_time - started_at).total_seconds() < self.timeout_seconds:
            return []
        pending_entries = self.journal.unfinished(session_id=session_id)
        return self._rollback_entries(session_id=session_id, entries=pending_entries)

    def resume(self, session_id: str) -> list[RollbackReport]:
        pending_entries = self.journal.unfinished(session_id=session_id)
        return self._rollback_entries(session_id=session_id, entries=pending_entries)

    def _rollback_entries(self, session_id: str, entries: list[RollbackEntry]) -> list[RollbackReport]:
        reports: list[RollbackReport] = []
        servers_by_name = {srv.name: srv for srv in self.config.servers}
        for entry in reversed(entries):
            if entry.session_id != session_id:
                continue
            server = servers_by_name.get(entry.target)
            if not server:
                continue
            self.guard.validate(target=entry.target, command=entry.recovery_action)
            result = self.channel.execute(
                HostSpec(name=server.name, host=server.host, user=server.user, port=server.port),
                entry.recovery_action,
                timeout=self.config.timeout,
            )
            reports.append(
                RollbackReport(host=entry.target, rollback_command=entry.recovery_action, success=result.success)
            )
            if result.success:
                self.journal.mark_completed(entry)
        return reports
