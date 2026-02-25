from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from fault_injector.reporting.timeline import TimelineEvent


@dataclass(slots=True)
class ResilienceScore:
    recovery_time_score: float
    error_impact_score: float
    slo_deviation_score: float
    total_score: float
    recovery_time_seconds: float
    affected_hosts: int
    error_rate: float
    slo_target: float
    slo_actual: float


def _parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def calculate_resilience_score(
    events: list[TimelineEvent],
    total_hosts: int,
    slo_target: float = 0.99,
) -> ResilienceScore:
    injection_times = [_parse_ts(e.timestamp) for e in events if e.event_type == "injection"]
    rollback_success_times = [
        _parse_ts(e.timestamp) for e in events if e.event_type == "rollback" and e.status == "success"
    ]
    if injection_times and rollback_success_times:
        recovery_seconds = max(0.0, (max(rollback_success_times) - min(injection_times)).total_seconds())
    else:
        recovery_seconds = 0.0

    action_events = [e for e in events if e.event_type in {"injection", "rollback"}]
    failed_actions = [e for e in action_events if e.status != "success"]
    error_rate = (len(failed_actions) / len(action_events)) if action_events else 0.0

    breached_samples = [e for e in events if e.event_type == "monitor" and e.status != "ok"]
    affected = {e.host for e in failed_actions}
    affected.update(e.host for e in breached_samples)
    affected_hosts = len(affected)

    slo_actual = 1.0 - error_rate
    slo_deviation = max(0.0, slo_target - slo_actual)

    recovery_time_score = max(0.0, 100.0 - recovery_seconds * 5.0)
    error_impact_score = max(0.0, 100.0 - error_rate * 100.0 - (affected_hosts / max(total_hosts, 1)) * 30.0)
    slo_deviation_score = max(0.0, 100.0 - slo_deviation * 300.0)

    total_score = recovery_time_score * 0.4 + error_impact_score * 0.3 + slo_deviation_score * 0.3

    return ResilienceScore(
        recovery_time_score=round(recovery_time_score, 2),
        error_impact_score=round(error_impact_score, 2),
        slo_deviation_score=round(slo_deviation_score, 2),
        total_score=round(total_score, 2),
        recovery_time_seconds=round(recovery_seconds, 3),
        affected_hosts=affected_hosts,
        error_rate=round(error_rate, 4),
        slo_target=slo_target,
        slo_actual=round(slo_actual, 4),
    )


def resilience_to_json(score: ResilienceScore) -> dict[str, object]:
    return asdict(score)
