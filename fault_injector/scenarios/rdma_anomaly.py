from __future__ import annotations

from datetime import datetime, timezone
import shlex
import time
from typing import TYPE_CHECKING

from channel.ssh import HostSpec
from fault_injector.config import InjectorConfig
from fault_injector.orchestrator.session import FaultStep
from fault_injector.safety.rollback import RollbackEntry

if TYPE_CHECKING:
    from fault_injector.injector import ActionReport, FaultInjector


class RDMAMtuAnomalyScenario:
    """Describe RDMA/ROCE MTU mismatch steps and parameters only."""

    name = "rdma_anomaly"

    @staticmethod
    def _build_set_mtu_command(interface: str, mtu: int) -> str:
        iface = shlex.quote(interface)
        return f"sudo ip link set dev {iface} mtu {int(mtu)}"

    def build_steps(self, config: InjectorConfig) -> list[FaultStep]:
        steps: list[FaultStep] = []
        for srv in config.servers:
            steps.append(
                FaultStep(
                    host=HostSpec(name=srv.name, host=srv.host, user=srv.user, port=srv.port),
                    inject_command=self._build_set_mtu_command(srv.interface, srv.fault_mtu),
                    rollback_command=self._build_set_mtu_command(srv.interface, srv.original_mtu),
                    parameters={
                        "interface": srv.interface,
                        "fault_mtu": srv.fault_mtu,
                        "original_mtu": srv.original_mtu,
                    },
                )
            )
        return steps

    def inject_roce_mtu_mismatch(self, injector: FaultInjector) -> list[ActionReport]:
        from fault_injector.injector import ActionReport

        reports: list[ActionReport] = []
        for step in self.build_steps(injector.config):
            injector.guard.validate(target=step.host.name, command=step.inject_command)
            injector.guard.validate(target=step.host.name, command=step.rollback_command)

            injector.journal.append(
                RollbackEntry.pending(
                    session_id=injector.session_id,
                    target=step.host.name,
                    recovery_action=step.rollback_command,
                )
            )

            start = time.perf_counter()
            result = injector.channel.execute(
                step.host,
                step.inject_command,
                timeout=injector.config.timeout,
                wal_payload={
                    "session_id": injector.session_id,
                    "host": step.host.name,
                    "rollback_command": step.rollback_command,
                },
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            reports.append(
                ActionReport(
                    host=step.host.name,
                    inject_command=step.inject_command,
                    rollback_command=step.rollback_command,
                    success=result.success,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    duration_ms=elapsed_ms,
                    error=result.stderr,
                )
            )
        return reports
