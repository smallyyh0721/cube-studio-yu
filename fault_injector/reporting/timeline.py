from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class MonitorSample:
    timestamp: str
    host: str
    metric: str
    value: float
    threshold: float
    status: str


@dataclass(slots=True)
class TimelineEvent:
    timestamp: str
    event_type: str
    host: str
    status: str
    title: str
    details: dict[str, object]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_timeline_events(
    inject_reports: list[object] | None = None,
    monitor_samples: list[MonitorSample] | None = None,
    rollback_reports: list[object] | None = None,
) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []

    for report in inject_reports or []:
        events.append(
            TimelineEvent(
                timestamp=getattr(report, "timestamp", "") or utc_now_iso(),
                event_type="injection",
                host=report.host,
                status="success" if report.success else "failed",
                title="Injected fault",
                details={
                    "inject_command": report.inject_command,
                    "rollback_command": report.rollback_command,
                    "duration_ms": getattr(report, "duration_ms", 0),
                    "error": getattr(report, "error", ""),
                },
            )
        )

    for sample in monitor_samples or []:
        events.append(
            TimelineEvent(
                timestamp=sample.timestamp,
                event_type="monitor",
                host=sample.host,
                status=sample.status,
                title=f"Metric sampled: {sample.metric}",
                details={
                    "metric": sample.metric,
                    "value": sample.value,
                    "threshold": sample.threshold,
                },
            )
        )

    for report in rollback_reports or []:
        events.append(
            TimelineEvent(
                timestamp=getattr(report, "timestamp", "") or utc_now_iso(),
                event_type="rollback",
                host=report.host,
                status="success" if report.success else "failed",
                title="Rollback executed",
                details={
                    "rollback_command": report.rollback_command,
                    "duration_ms": getattr(report, "duration_ms", 0),
                    "error": getattr(report, "error", ""),
                },
            )
        )

    events.sort(key=lambda item: item.timestamp)
    return events


def timeline_to_json(events: list[TimelineEvent]) -> list[dict[str, object]]:
    return [asdict(event) for event in events]
