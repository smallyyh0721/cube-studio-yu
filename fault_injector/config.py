from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(slots=True)
class ConfigValidationIssue:
    path: str
    message: str


class ConfigValidationError(ValueError):
    def __init__(self, issues: list[ConfigValidationIssue]) -> None:
        self.issues = issues
        text = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Invalid config: {text}")


@dataclass(slots=True)
class ServerConfig:
    name: str
    host: str
    user: str
    port: int
    interface: str
    original_mtu: int
    fault_mtu: int


@dataclass(slots=True)
class InjectorConfig:
    mode: str
    wal_path: str
    timeout: int
    servers: list[ServerConfig]


def _is_positive_int(value: object) -> bool:
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


def validate_config_data(data: dict) -> list[ConfigValidationIssue]:
    issues: list[ConfigValidationIssue] = []

    if not isinstance(data, dict):
        return [ConfigValidationIssue(path="$", message="config root must be an object")]

    injector = data.get("injector")
    if injector is None:
        issues.append(ConfigValidationIssue(path="injector", message="missing required section"))
    elif not isinstance(injector, dict):
        issues.append(ConfigValidationIssue(path="injector", message="must be an object"))
    else:
        if "timeout" in injector and not _is_positive_int(injector["timeout"]):
            issues.append(ConfigValidationIssue(path="injector.timeout", message="must be > 0"))

    servers = data.get("servers")
    if servers is None:
        issues.append(ConfigValidationIssue(path="servers", message="missing required section"))
    elif not isinstance(servers, list) or not servers:
        issues.append(ConfigValidationIssue(path="servers", message="must be a non-empty array"))
    else:
        required = ("name", "host", "user", "interface", "original_mtu", "fault_mtu")
        for index, item in enumerate(servers):
            prefix = f"servers[{index}]"
            if not isinstance(item, dict):
                issues.append(ConfigValidationIssue(path=prefix, message="must be an object"))
                continue
            for field in required:
                if field not in item:
                    issues.append(ConfigValidationIssue(path=f"{prefix}.{field}", message="is required"))
            if "original_mtu" in item and not _is_positive_int(item["original_mtu"]):
                issues.append(ConfigValidationIssue(path=f"{prefix}.original_mtu", message="must be > 0"))
            if "fault_mtu" in item and not _is_positive_int(item["fault_mtu"]):
                issues.append(ConfigValidationIssue(path=f"{prefix}.fault_mtu", message="must be > 0"))

    return issues


def load_config(path: str) -> InjectorConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    issues = validate_config_data(data)
    if issues:
        raise ConfigValidationError(issues)

    injector = data["injector"]
    servers = [
        ServerConfig(
            name=item["name"],
            host=item["host"],
            user=item["user"],
            port=int(item.get("port", 22)),
            interface=item["interface"],
            original_mtu=int(item["original_mtu"]),
            fault_mtu=int(item["fault_mtu"]),
        )
        for item in data["servers"]
    ]
    return InjectorConfig(
        mode=injector.get("mode", "simulate"),
        wal_path=injector.get("wal_path", "fault_injector/rollback.wal"),
        timeout=int(injector.get("timeout", 20)),
        servers=servers,
    )
