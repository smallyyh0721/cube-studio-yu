from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from channel.ssh import SSHChannel
from fault_injector.config import InjectorConfig
from fault_injector.scenarios.rdma_anomaly import RDMAMtuAnomalyScenario
from fault_injector.safety.guard import SafetyGuard
from fault_injector.safety.rollback import RollbackJournal
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
        self.channel = SSHChannel(mode=config.mode, wal_hook=self._wal_prewrite)
        self.journal = RollbackJournal(config.wal_path)
        authorized_targets = {srv.name for srv in config.servers}
        self.guard = SafetyGuard(authorized_targets=authorized_targets)
        self.scenario = RDMAMtuAnomalyScenario()
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
        return self.scenario.inject_roce_mtu_mismatch(self)

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

    def _wal_prewrite(self, payload: dict[str, str]) -> None:
        # Entries are appended in scenario execution before command dispatch.
        _ = payload
