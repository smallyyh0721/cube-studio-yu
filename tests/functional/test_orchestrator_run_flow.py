from __future__ import annotations

import json
from pathlib import Path

import pytest

from fault_injector.config import load_config
from fault_injector.injector import FaultInjector
from fault_injector.orchestrator import FaultInjectionOrchestrator


class MockMonitor:
    def __init__(self, *, rollback_required: bool, timed_out: bool = False) -> None:
        self._rollback_required = rollback_required
        self._timed_out = timed_out

    def observe(self) -> dict[str, bool]:
        return {"rollback_required": self._rollback_required, "timed_out": self._timed_out}


def _write_config(path: Path, wal_path: Path) -> None:
    payload = {
        "injector": {"mode": "simulate", "wal_path": str(wal_path), "timeout": 20},
        "servers": [
            {
                "name": "node-a",
                "host": "127.0.0.1",
                "user": "root",
                "interface": "eth0",
                "original_mtu": 4200,
                "fault_mtu": 1500,
            },
            {
                "name": "node-b",
                "host": "127.0.0.2",
                "user": "root",
                "interface": "eth0",
                "original_mtu": 4200,
                "fault_mtu": 9000,
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("scenario_family", ["RC", "F"])
@pytest.mark.parametrize(
    ("case_name", "inject_fail_hosts", "timed_out", "rollback_fail_attempts", "expected_status"),
    [
        ("success", set(), False, 0, "success"),
        ("partial_failure", {"node-b"}, False, 0, "rolled_back"),
        ("timeout", set(), True, 0, "timeout"),
        ("rollback_retry", {"node-a"}, False, 1, "rolled_back"),
    ],
)
def test_orchestrator_run_includes_wal_first_and_recovery_paths(
    tmp_path: Path,
    scenario_family: str,
    case_name: str,
    inject_fail_hosts: set[str],
    timed_out: bool,
    rollback_fail_attempts: int,
    expected_status: str,
) -> None:
    wal_path = tmp_path / f"{scenario_family}-{case_name}.wal"
    conf_path = tmp_path / f"{scenario_family}-{case_name}.json"
    _write_config(conf_path, wal_path)

    injector = FaultInjector(load_config(str(conf_path)), session_id=f"{scenario_family}-{case_name}")

    base_execute = injector.channel.execute
    call_state = {"rollback_calls": 0}

    def execute_with_failures(host_spec, remote_command, timeout=20):
        wal_entries = injector.journal.load(injector.session_id)
        if "mtu" in remote_command and "4200" not in remote_command:
            assert any(entry.host == host_spec.name for entry in wal_entries), "WAL must be written before injection"
            result = base_execute(host_spec, remote_command, timeout)
            if host_spec.name in inject_fail_hosts:
                result.success = False
            return result

        if "mtu 4200" in remote_command and rollback_fail_attempts:
            if call_state["rollback_calls"] < rollback_fail_attempts:
                call_state["rollback_calls"] += 1
                result = base_execute(host_spec, remote_command, timeout)
                result.success = False
                return result

        return base_execute(host_spec, remote_command, timeout)

    injector.channel.execute = execute_with_failures  # type: ignore[assignment]

    monitor = MockMonitor(
        rollback_required=bool(inject_fail_hosts),
        timed_out=timed_out,
    )
    orchestrator = FaultInjectionOrchestrator(injector, monitor, rollback_retries=2)

    result = orchestrator.run()

    assert result.status == expected_status
    assert len(result.reports) == 2
    if inject_fail_hosts:
        assert result.rollback_attempts >= 1
