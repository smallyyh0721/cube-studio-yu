from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
import shlex
import uuid

from fault_injector.config import InjectorConfig
from fault_injector.orchestrator.engine import FaultOrchestratorEngine


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
        self.channel = SSHChannel(mode=config.mode, wal_hook=self._wal_prewrite)

        for srv in config.servers:
            self.channel.seed_simulated_mtu(srv.name, srv.interface, srv.original_mtu)

    def inject_roce_mtu_mismatch(self) -> list[ActionReport]:
        reports: list[ActionReport] = []
        for srv in self.config.servers:
            inject_command = self._build_set_mtu_command(srv.interface, srv.fault_mtu)
            rollback_command = self._build_set_mtu_command(srv.interface, srv.original_mtu)

            self.journal.record(
                RollbackEntry(
                    session_id=self.session_id,
                    host=srv.name,
                    rollback_command=rollback_command,
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
        reports: list[ActionReport] = []
        entries = self.journal.load(self.session_id)
        for entry in reversed(entries):
            srv = next(s for s in self.config.servers if s.name == entry.host)
            start = time.perf_counter()
            result = self.channel.execute(
                HostSpec(name=srv.name, host=srv.host, user=srv.user, port=srv.port),
                entry.rollback_command,
                timeout=self.config.timeout,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            reports.append(
                ActionReport(
                    host=entry.host,
                    inject_command="",
                    rollback_command=entry.rollback_command,
                    success=result.success,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    duration_ms=elapsed_ms,
                    error=result.stderr,
                )
            )
        self.journal.remove_session(self.session_id)
        return reports

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
