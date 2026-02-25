from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on runtime deps
    yaml = None
from pydantic import ValidationError

from fault_injector.config.defaults import clone_default_config
from fault_injector.config.schema import FaultInjectorConfigModel


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_raw_config(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        if yaml is None:
            raise ValueError(
                "YAML support requires PyYAML. Install `pyyaml` or provide a JSON config file."
            )
        data = yaml.safe_load(raw)

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be an object/mapping, got: {type(data).__name__}")
    return data


def _expected_type(error_type: str) -> str:
    mapping = {
        "int_parsing": "integer",
        "string_type": "string",
        "literal_error": "one of allowed literal values",
        "list_type": "array",
        "dict_type": "object",
        "missing": "required field",
        "bool_type": "boolean",
    }
    return mapping.get(error_type, error_type)


def _format_validation_error(config_path: Path, exc: ValidationError) -> str:
    lines = [f"Config validation failed: {config_path}"]
    for err in exc.errors(include_url=False):
        loc = ".".join(str(part) for part in err.get("loc", ())) or "<root>"
        message = err.get("msg", "validation error")
        type_name = _expected_type(err.get("type", "unknown"))
        input_value = err.get("input")
        actual_type = type(input_value).__name__ if input_value is not None else "null"
        lines.append(
            f"- field='{loc}' expected={type_name} actual={actual_type} message='{message}'"
        )
    return "\n".join(lines)


def load_typed_config(path: str | Path) -> FaultInjectorConfigModel:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")

    try:
        user_config = _load_raw_config(p)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON config at {p}: {exc}") from exc
    except Exception as exc:
        if yaml is not None and isinstance(exc, yaml.YAMLError):
            raise ValueError(f"Failed to parse YAML config at {p}: {exc}") from exc
        raise

    merged = _deep_merge(clone_default_config(), user_config)

    try:
        return FaultInjectorConfigModel.model_validate(merged)
    except ValidationError as exc:
        raise ValueError(_format_validation_error(p, exc)) from exc
