from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fault_injector.config import load_config

try:
    from fault_injector.config.loader import load_typed_config
except ModuleNotFoundError:
    load_typed_config = None

try:
    import yaml as _yaml  # noqa: F401
except ModuleNotFoundError:
    _HAS_YAML = False
else:
    _HAS_YAML = True


@unittest.skipUnless(load_typed_config is not None, "pydantic is required for typed config loader tests")
class ConfigLoaderTests(unittest.TestCase):
    @unittest.skipUnless(_HAS_YAML, "PyYAML is required for YAML parsing tests")
    def test_load_yaml_and_merge_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            config_path = Path(td) / "injector.yaml"
            config_path.write_text(
                """
injector:
  mode: simulate
scenario:
  servers:
    - name: node-a
      host: 127.0.0.1
      user: root
      interface: eth0
      original_mtu: 4200
      fault_mtu: 1500
""",
                encoding="utf-8",
            )

            loaded = load_typed_config(config_path)
            self.assertEqual("fault_injector/rollback.wal", loaded.injector.wal_path)
            self.assertEqual(20, loaded.injector.timeout)
            self.assertEqual(22, loaded.scenario.servers[0].port)

    def test_legacy_load_config_still_supports_servers_root_key(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            config_path = Path(td) / "injector.json"
            config_path.write_text(
                """{
  "injector": {"mode": "simulate"},
  "servers": [
    {
      "name": "node-a",
      "host": "127.0.0.1",
      "user": "root",
      "interface": "eth0",
      "original_mtu": 4200,
      "fault_mtu": 1500
    }
  ]
}""",
                encoding="utf-8",
            )

            legacy = load_config(str(config_path))
            self.assertEqual("simulate", legacy.mode)
            self.assertEqual(1, len(legacy.servers))
            self.assertEqual(22, legacy.servers[0].port)

    def test_validation_error_contains_path_field_and_type(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            config_path = Path(td) / "injector.json"
            config_path.write_text(
                """{
  "scenario": {
    "servers": [
      {
        "name": "node-a",
        "host": "",
        "user": "root",
        "interface": "eth0",
        "original_mtu": "abc",
        "fault_mtu": 1500
      }
    ]
  }
}""",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as ctx:
                load_typed_config(config_path)

            msg = str(ctx.exception)
            self.assertIn(str(config_path), msg)
            self.assertIn("scenario.servers.0.host", msg)
            self.assertIn("scenario.servers.0.original_mtu", msg)
            self.assertIn("expected=integer", msg)


if __name__ == "__main__":
    unittest.main()
