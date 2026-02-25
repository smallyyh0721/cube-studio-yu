from __future__ import annotations

import json
from pathlib import Path

from fault_injector.config import load_config


def test_load_config_with_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "injector.json"
    payload = {
        "injector": {"wal_path": str(tmp_path / "rollback.wal")},
        "servers": [
            {
                "name": "node-a",
                "host": "127.0.0.1",
                "user": "root",
                "interface": "eth0",
                "original_mtu": 4200,
                "fault_mtu": 1500,
            }
        ],
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    config = load_config(str(config_path))

    assert config.mode == "simulate"
    assert config.timeout == 20
    assert config.servers[0].port == 22
    assert config.servers[0].fault_mtu == 1500
