from __future__ import annotations

import json
import sys
from enum import IntEnum

from fault_injector.cli import (
    CLIArgumentError,
    CLIConfigError,
    CLIExecutionError,
    CLIRollbackError,
    build_parser,
    execute,
    render_output,
)


class ExitCode(IntEnum):
    OK = 0
    ARGUMENT_ERROR = 2
    CONFIG_ERROR = 3
    EXECUTION_ERROR = 4
    ROLLBACK_ERROR = 5


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        payload = execute(args)
        render_output(payload, as_json=bool(args.json_output))
        return int(ExitCode.OK)
    except CLIArgumentError as exc:
        return _emit_error(ExitCode.ARGUMENT_ERROR, "argument_error", exc, argv)
    except SystemExit as exc:
        return int(exc.code)
    except CLIConfigError as exc:
        return _emit_error(ExitCode.CONFIG_ERROR, "config_error", exc, argv)
    except CLIRollbackError as exc:
        return _emit_error(ExitCode.ROLLBACK_ERROR, "rollback_error", exc, argv)
    except CLIExecutionError as exc:
        return _emit_error(ExitCode.EXECUTION_ERROR, "execution_error", exc, argv)


def _emit_error(code: ExitCode, kind: str, exc: Exception, argv: list[str] | None) -> int:
    wants_json = bool(argv and "--json" in argv)
    message: object
    if exc.args and isinstance(exc.args[0], dict):
        message = exc.args[0]
    else:
        try:
            message = json.loads(str(exc))
        except json.JSONDecodeError:
            message = str(exc)

    payload = {
        "ok": False,
        "error": {
            "type": kind,
            "message": message,
            "exit_code": int(code),
        },
    }

    if wants_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
    else:
        print(f"{kind}: {message}", file=sys.stderr)
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
