from __future__ import annotations

import pytest

from fault_injector.scenario_registry import ScenarioRegistry


def test_scenario_registry_register_get_and_list() -> None:
    registry = ScenarioRegistry()
    registry.register("rc/roce_mtu_mismatch", lambda: "ok")

    assert registry.list() == ["rc/roce_mtu_mismatch"]
    assert registry.get("rc/roce_mtu_mismatch")() == "ok"



def test_scenario_registry_duplicate_and_missing() -> None:
    registry = ScenarioRegistry()
    registry.register("f/node_restart", lambda: "ok")

    with pytest.raises(ValueError):
        registry.register("f/node_restart", lambda: "another")

    with pytest.raises(KeyError):
        registry.get("missing")
