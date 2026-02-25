from __future__ import annotations

from collections import defaultdict

from fault_injector.reporting.timeline import TimelineEvent


def build_chart_data(events: list[TimelineEvent]) -> dict[str, object]:
    labels = [event.timestamp for event in events]
    success_counter = 0
    failure_counter = 0
    cumulative_success: list[int] = []
    cumulative_failure: list[int] = []

    monitor_series: dict[str, list[dict[str, object]]] = defaultdict(list)

    for event in events:
        if event.event_type in {"injection", "rollback"}:
            if event.status == "success":
                success_counter += 1
            else:
                failure_counter += 1
        cumulative_success.append(success_counter)
        cumulative_failure.append(failure_counter)

        if event.event_type == "monitor":
            metric = str(event.details.get("metric", "unknown"))
            key = f"{event.host}:{metric}"
            monitor_series[key].append(
                {
                    "timestamp": event.timestamp,
                    "value": event.details.get("value"),
                    "threshold": event.details.get("threshold"),
                    "status": event.status,
                }
            )

    return {
        "timeline": {
            "labels": labels,
            "cumulative_success": cumulative_success,
            "cumulative_failure": cumulative_failure,
        },
        "monitor_metrics": dict(monitor_series),
    }
