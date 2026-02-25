from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from fault_injector.config import InjectorConfig
from fault_injector.injector import ActionReport, FaultInjector
from fault_injector.reporting.charts import build_chart_data
from fault_injector.reporting.html_report import render_html_report
from fault_injector.reporting.resilience import calculate_resilience_score, resilience_to_json
from fault_injector.reporting.timeline import MonitorSample, build_timeline_events, timeline_to_json, utc_now_iso


class FaultInjectionOrchestrator:
    def __init__(self, config: InjectorConfig, session_id: str) -> None:
        self.config = config
        self.session_id = session_id
        self.injector = FaultInjector(config=config, session_id=session_id)

    def run(self, command: str, output_dir: str = "fault_injector/reports") -> dict[str, object]:
        inject_reports: list[ActionReport] = []
        rollback_reports: list[ActionReport] = []

        if command == "inject-roce-mtu-mismatch":
            inject_reports = self.injector.inject_roce_mtu_mismatch()
        elif command == "rollback":
            rollback_reports = self.injector.rollback()
        else:
            raise ValueError(f"Unsupported command: {command}")

        monitor_samples = self._collect_monitor_samples()
        events = build_timeline_events(inject_reports, monitor_samples, rollback_reports)
        score = calculate_resilience_score(events, total_hosts=len(self.config.servers))

        report = {
            "scenario": {
                "session_id": self.session_id,
                "command": command,
                "mode": self.config.mode,
                "server_count": len(self.config.servers),
                "servers": [asdict(item) for item in self.config.servers],
            },
            "actions": {
                "inject": [asdict(item) for item in inject_reports],
                "rollback": [asdict(item) for item in rollback_reports],
            },
            "timeline": timeline_to_json(events),
            "resilience_score": resilience_to_json(score),
            "charts": build_chart_data(events),
        }

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / f"report_{self.session_id}.json"
        html_path = out / f"report_{self.session_id}.html"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(render_html_report(report), encoding="utf-8")

        return {
            "report": report,
            "report_json": str(json_path),
            "report_html": str(html_path),
            "inject_reports": inject_reports,
            "rollback_reports": rollback_reports,
        }

    def _collect_monitor_samples(self) -> list[MonitorSample]:
        samples: list[MonitorSample] = []
        for srv in self.config.servers:
            current = self.injector.channel.get_simulated_mtu(srv.name, srv.interface)
            if current is None:
                continue
            deviation = abs(current - srv.original_mtu)
            samples.append(
                MonitorSample(
                    timestamp=utc_now_iso(),
                    host=srv.name,
                    metric="mtu_deviation",
                    value=float(deviation),
                    threshold=0.0,
                    status="ok" if deviation == 0 else "warn",
                )
            )
        return samples
