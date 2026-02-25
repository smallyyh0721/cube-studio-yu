from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


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


def _load_legacy_json_config(path: str) -> InjectorConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    injector = data.get("injector", {})
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
        for item in data.get("servers", [])
    ]
    return InjectorConfig(
        mode=injector.get("mode", "simulate"),
        wal_path=injector.get("wal_path", "fault_injector/rollback.wal"),
        timeout=int(injector.get("timeout", 20)),
        servers=servers,
    )


def load_typed_config(path: str):
    from fault_injector.config.loader import load_typed_config as _load_typed_config

    return _load_typed_config(path)


def load_config(path: str) -> InjectorConfig:
    try:
        typed = load_typed_config(path)
    except ModuleNotFoundError as exc:  # pragma: no cover - fallback for minimal envs
        if exc.name != "pydantic":
            raise
        return _load_legacy_json_config(path)

    return InjectorConfig(
        mode=typed.injector.mode,
        wal_path=typed.injector.wal_path,
        timeout=typed.injector.timeout,
        servers=[
            ServerConfig(
                name=item.name,
                host=item.host,
                user=item.user,
                port=item.port,
                interface=item.interface,
                original_mtu=item.original_mtu,
                fault_mtu=item.fault_mtu,
            )
            for item in typed.scenario.servers
        ],
    )


__all__ = ["InjectorConfig", "ServerConfig", "load_config", "load_typed_config"]
