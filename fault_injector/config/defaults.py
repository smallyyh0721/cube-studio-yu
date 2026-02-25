from __future__ import annotations

import copy

DEFAULT_CONFIG_DICT: dict[str, object] = {
    "injector": {
        "mode": "simulate",
        "wal_path": "fault_injector/rollback.wal",
        "timeout": 20,
    },
    "channel": {
        "connect_timeout": 10,
        "command_timeout": 20,
        "retries": 0,
    },
    "safety": {
        "dry_run": False,
        "require_root": True,
        "max_parallel_hosts": 8,
    },
    "scenario": {
        "name": "roce_mtu_mismatch",
        "servers": [],
    },
    "reporting": {
        "format": "json",
        "output_path": "fault_injector/report.json",
        "include_commands": True,
    },
}

DEFAULT_CONFIG_YAML = """\
injector:
  mode: simulate
  wal_path: fault_injector/rollback.wal
  timeout: 20

channel:
  connect_timeout: 10
  command_timeout: 20
  retries: 0

safety:
  dry_run: false
  require_root: true
  max_parallel_hosts: 8

scenario:
  name: roce_mtu_mismatch
  servers: []

reporting:
  format: json
  output_path: fault_injector/report.json
  include_commands: true
"""


def clone_default_config() -> dict[str, object]:
    return copy.deepcopy(DEFAULT_CONFIG_DICT)
