from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fault_injector.config import load_config
from fault_injector.injector import FaultInjector
from fault_injector.safety.guard import SafetyGuard, SafetyViolationError
from fault_injector.safety.rollback import RollbackJournal


class SafetyAndResumeTests(unittest.TestCase):
    def test_guard_blocks_unauthorized_and_dangerous_command(self) -> None:
        guard = SafetyGuard(authorized_targets={"node-a"})

        with self.assertRaises(SafetyViolationError):
            guard.validate(target="node-b", command="echo ok")

        with self.assertRaises(SafetyViolationError):
            guard.validate(target="node-a", command="rm -rf /")

    def test_resume_and_timeout_rollback_only_handle_current_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wal_path = Path(td) / "rollback.wal"
            conf_path = Path(td) / "injector.conf.json"
            conf_path.write_text(
                """{
  "injector": {
    "mode": "simulate",
    "wal_path": "%s",
    "timeout": 1
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
    },
    {
      "name": "node-b",
      "host": "127.0.0.2",
      "user": "root",
      "port": 22,
      "interface": "eth0",
      "original_mtu": 4200,
      "fault_mtu": 9000
    }
  ]
}""" % wal_path,
                encoding="utf-8",
            )

            config = load_config(str(conf_path))
            injector_t1 = FaultInjector(config, session_id="t1")
            injector_t2 = FaultInjector(config, session_id="t2")
            injector_t1.inject_roce_mtu_mismatch()
            injector_t2.inject_roce_mtu_mismatch()

            timeout_reports = injector_t1.rollback_on_timeout(
                started_at=datetime.now(timezone.utc) - timedelta(seconds=5)
            )
            self.assertEqual(2, len(timeout_reports))
            self.assertEqual(4200, injector_t1.channel.get_simulated_mtu("node-a", "eth0"))

            journal = RollbackJournal(str(wal_path))
            remaining_t1 = journal.unfinished(session_id="t1")
            remaining_t2 = journal.unfinished(session_id="t2")
            self.assertEqual([], remaining_t1)
            self.assertEqual(2, len(remaining_t2))

            injector_t2_resume = FaultInjector(config, session_id="t2")
            resume_reports = injector_t2_resume.resume_rollback()
            self.assertEqual(2, len(resume_reports))
            self.assertEqual([], journal.unfinished(session_id="t2"))


if __name__ == "__main__":
    unittest.main()
