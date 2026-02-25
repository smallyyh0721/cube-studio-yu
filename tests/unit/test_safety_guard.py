from __future__ import annotations

import pytest

from fault_injector.safety_guard import SafetyGuard


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("sudo ip link set dev eth0 mtu 1500", True),
        ("rm -rf /", False),
        ("sudo reboot", False),
    ],
)
def test_safety_guard_blocks_dangerous_commands(command: str, expected: bool) -> None:
    guard = SafetyGuard()
    assert guard.is_allowed(command) is expected
