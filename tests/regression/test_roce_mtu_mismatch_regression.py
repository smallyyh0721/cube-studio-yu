from __future__ import annotations

import json
from pathlib import Path

from fault_injector.config import load_config
from fault_injector.injector import FaultInjector


def _write_config(path: Path, wal_path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "injector": {"mode": "simulate", "wal_path": str(wal_path), "timeout": 20},
                "servers": [
                    {
                        "name": "node-a",
                        "host": "127.0.0.1",
                        "user": "root",
                        "port": 22,
                        "interface": "eth0",
                        "original_mtu": 4200,
                        "fault_mtu": 1500,
                    },
                    {
                        "name": "node-b",
                        "host": "127.0.0.2",
                        "user": "root",
                        "port": 22,
                        "interface": "eth0",
                        "original_mtu": 4200,
                        "fault_mtu": 9000,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_regression_keeps_previous_roce_inject_and_rollback_behavior(tmp_path: Path) -> None:
    wal_path = tmp_path / "rollback.wal"
    conf_path = tmp_path / "injector.conf.json"
    _write_config(conf_path, wal_path)

    injector = FaultInjector(load_config(str(conf_path)), session_id="t1")
    reports = injector.inject_roce_mtu_mismatch()

    assert len(reports) == 2
    assert "mtu 1500" in reports[0].inject_command
    assert "mtu 9000" in reports[1].inject_command
    assert injector.channel.get_simulated_mtu("node-a", "eth0") == 1500
    assert injector.channel.get_simulated_mtu("node-b", "eth0") == 9000

    rollback_reports = injector.rollback()
    assert len(rollback_reports) == 2
    assert injector.channel.get_simulated_mtu("node-a", "eth0") == 4200
    assert injector.channel.get_simulated_mtu("node-b", "eth0") == 4200
