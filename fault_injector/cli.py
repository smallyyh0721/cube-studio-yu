from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from fault_injector.config import ConfigValidationError, load_config, validate_config_data
from fault_injector.orchestrator.engine import FaultOrchestrator
from fault_injector.scenarios.registry import list_scenarios


class CLIArgumentError(Exception):
    pass


class CLIConfigError(Exception):
    pass


class CLIExecutionError(Exception):
    pass


class CLIRollbackError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CLIArgumentError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(description="Cube Studio fault injector")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit machine-readable JSON output")

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


def execute(args: argparse.Namespace) -> dict:
    if args.command == "run":
        try:
            config = load_config(args.config)
        except ConfigValidationError as exc:
            raise CLIConfigError(_validation_payload(exc)) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise CLIConfigError({"valid": False, "errors": [{"path": "$", "message": str(exc)}]}) from exc

        orchestrator = FaultOrchestrator(config)
        try:
            return orchestrator.run(
                scenario=args.scenario,
                session_id=args.session_id,
                only=list(args.only),
                resume=bool(args.resume),
            )
        except ValueError as exc:
            raise CLIExecutionError(str(exc)) from exc
        except RuntimeError as exc:
            message = str(exc)
            if "rollback" in message.lower():
                raise CLIRollbackError(message) from exc
            raise CLIExecutionError(message) from exc

    if args.command == "validate-config":
        path = Path(args.config)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CLIConfigError({"valid": False, "errors": [{"path": "$", "message": str(exc)}]}) from exc

        issues = validate_config_data(data)
        return {
            "valid": not issues,
            "errors": [asdict(item) for item in issues],
            "config": str(path),
        }

    scenarios = [
        {
            "scenario": item.scenario_id,
            "code": item.code,
            "description": item.description,
            "rollback_supported": item.rollback_supported,
        }
        for item in list_scenarios()
    ]
    return {"scenarios": scenarios}


def _validation_payload(exc: ConfigValidationError) -> dict:
    return {
        "valid": False,
        "errors": [asdict(item) for item in exc.issues],
    }


def render_output(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(json.dumps(payload, ensure_ascii=False, indent=2))
