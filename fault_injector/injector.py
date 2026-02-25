from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import shlex
import uuid

from fault_injector.config import InjectorConfig
from fault_injector.safety.guard import SafetyGuard
from fault_injector.safety.rollback import RollbackEntry, RollbackJournal
from orchestrator.watchdog import SessionWatchdog


@dataclass(slots=True)
class ActionReport:
    host: str
    inject_command: str
    rollback_command: str
    success: bool
    timestamp: str = ""
    duration_ms: int = 0
    error: str = ""


class FaultInjector:
    """Backward-compatible facade that forwards to the new orchestrator engine."""

    def __init__(self, config: InjectorConfig, session_id: str | None = None) -> None:
        self.config = config
        self.session_id = session_id or uuid.uuid4().hex
        self.journal = RollbackJournal(config.wal_path)
        authorized_targets = {srv.name for srv in config.servers}
        self.guard = SafetyGuard(authorized_targets=authorized_targets)
        self.watchdog = SessionWatchdog(
            timeout_seconds=config.timeout,
            config=config,
            journal=self.journal,
            channel=self.channel,
            guard=self.guard,
        )

        for srv in config.servers:
            self.channel.seed_simulated_mtu(srv.name, srv.interface, srv.original_mtu)

    def inject_roce_mtu_mismatch(self) -> list[ActionReport]:
        reports: list[ActionReport] = []
        for srv in self.config.servers:
            inject_command = self._build_set_mtu_command(srv.interface, srv.fault_mtu)
            rollback_command = self._build_set_mtu_command(srv.interface, srv.original_mtu)

            self.guard.validate(target=srv.name, command=inject_command)
            self.guard.validate(target=srv.name, command=rollback_command)

            self.journal.append(
                RollbackEntry.pending(
                    session_id=self.session_id,
                    target=srv.name,
                    recovery_action=rollback_command,
                )
            )

            start = time.perf_counter()
            result = self.channel.execute(
                HostSpec(name=srv.name, host=srv.host, user=srv.user, port=srv.port),
                inject_command,
                timeout=self.config.timeout,
                wal_payload={
                    "session_id": self.session_id,
                    "host": srv.name,
                    "rollback_command": rollback_command,
                },
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            reports.append(
                ActionReport(
                    host=srv.name,
                    inject_command=inject_command,
                    rollback_command=rollback_command,
                    success=result.success,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    duration_ms=elapsed_ms,
                    error=result.stderr,
                )
            )
        return reports

    def rollback(self) -> list[ActionReport]:
        rollback_reports = self.watchdog.resume(session_id=self.session_id)
        return [
            ActionReport(host=r.host, inject_command="", rollback_command=r.rollback_command, success=r.success)
            for r in rollback_reports
        ]

    def rollback_on_timeout(self, started_at: datetime, now: datetime | None = None) -> list[ActionReport]:
        rollback_reports = self.watchdog.trigger_timeout_rollback(
            session_id=self.session_id,
            started_at=started_at,
            now=now or datetime.now(timezone.utc),
        )
        return [
            ActionReport(host=r.host, inject_command="", rollback_command=r.rollback_command, success=r.success)
            for r in rollback_reports
        ]

    def resume_rollback(self) -> list[ActionReport]:
        return self.rollback()

    @staticmethod
    def _build_set_mtu_command(interface: str, mtu: int) -> str:
        iface = shlex.quote(interface)
        return f"sudo ip link set dev {iface} mtu {int(mtu)}"

    def _wal_prewrite(self, payload: dict[str, str]) -> None:
        self.journal.record(
            RollbackEntry(
                session_id=payload["session_id"],
                host=payload["host"],
                rollback_command=payload["rollback_command"],
            )
        )
