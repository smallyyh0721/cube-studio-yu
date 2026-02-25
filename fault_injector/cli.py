from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from fault_injector.config import load_config
from fault_injector.orchestrator import FaultInjectionOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cube Studio fault injector")
    parser.add_argument("--config", required=True, help="Path to injector conf json config")
    parser.add_argument("--session-id", default="demo-session", help="Session id for WAL")
    parser.add_argument(
        "--report-dir",
        default="fault_injector/reports",
        help="Directory to write report.json and report.html",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run fault scenario")
    run.add_argument("--config", required=True, help="Path to injector conf json config")
    run.add_argument("--scenario", required=True, help="Scenario id")
    run.add_argument("--session-id", required=True, help="Session id for WAL")
    run.add_argument("--only", nargs="+", default=[], help="Only run against these server names")
    run.add_argument("--resume", action="store_true", help="Rollback previous WAL entries before run")

    validate = subparsers.add_parser("validate-config", help="Validate config file")
    validate.add_argument("--config", required=True, help="Path to injector conf json config")

    subparsers.add_parser("list-scenarios", help="List available scenarios")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    orchestrator = FaultInjectionOrchestrator(config=config, session_id=args.session_id)
    run_result = orchestrator.run(command=args.command, output_dir=args.report_dir)

    if args.command == "inject-roce-mtu-mismatch":
        action_report = run_result["inject_reports"]
    else:
        action_report = run_result["rollback_reports"]

    print(json.dumps([asdict(item) for item in action_report], ensure_ascii=False, indent=2))
    print(f"report.json: {run_result['report_json']}")
    print(f"report.html: {run_result['report_html']}")

def render_output(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(json.dumps(payload, ensure_ascii=False, indent=2))
