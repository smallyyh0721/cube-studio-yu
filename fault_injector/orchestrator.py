from __future__ import annotations

from dataclasses import dataclass

from fault_injector.injector import ActionReport, FaultInjector


@dataclass(slots=True)
class OrchestratorResult:
    status: str
    reports: list[ActionReport]
    observations: dict[str, object]
    rollback_attempts: int


class FaultInjectionOrchestrator:
    """Drive run -> inject -> observe -> rollback -> report flow."""

    def __init__(
        self,
        injector: FaultInjector,
        monitor: object,
        rollback_retries: int = 1,
    ) -> None:
        self.injector = injector
        self.monitor = monitor
        self.rollback_retries = rollback_retries

    def run(self) -> OrchestratorResult:
        inject_reports = self.injector.inject_roce_mtu_mismatch()
        observations = self.monitor.observe()

        should_rollback = (
            observations.get("rollback_required", False)
            or not all(item.success for item in inject_reports)
        )

        status = "success"
        rollback_attempts = 0
        if should_rollback:
            status = "rolled_back"
            for _ in range(self.rollback_retries + 1):
                rollback_attempts += 1
                rollback_reports = self.injector.rollback()
                if all(item.success for item in rollback_reports):
                    break
            else:
                status = "rollback_failed"

        if observations.get("timed_out"):
            status = "timeout"

        return OrchestratorResult(
            status=status,
            reports=inject_reports,
            observations=observations,
            rollback_attempts=rollback_attempts,
        )
