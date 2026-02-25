from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fault_injector.config import load_config
from fault_injector.orchestrator import FaultInjectionOrchestrator


class ReportingTests(unittest.TestCase):
    def test_orchestrator_generates_json_and_html_reports(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            wal_path = td_path / "rollback.wal"
            conf_path = td_path / "injector.conf.json"
            conf_path.write_text(
                """{
  "injector": {
    "mode": "simulate",
    "wal_path": "%s",
    "timeout": 20
  },
  "servers": [
    {
      "name": "node-a",
      "host": "127.0.0.1",
      "user": "root",
      "port": 22,
      "interface": "eth0",
      "original_mtu": 4200,
      "fault_mtu": 1500
    }
  ]
}"""
                % wal_path,
                encoding="utf-8",
            )

            orchestrator = FaultInjectionOrchestrator(load_config(str(conf_path)), session_id="report-t1")
            result = orchestrator.run(command="inject-roce-mtu-mismatch", output_dir=str(td_path / "reports"))

            self.assertTrue(Path(result["report_json"]).exists())
            self.assertTrue(Path(result["report_html"]).exists())
            self.assertTrue(result["report"]["timeline"])
            self.assertIn("resilience_score", result["report"])


if __name__ == "__main__":
    unittest.main()
