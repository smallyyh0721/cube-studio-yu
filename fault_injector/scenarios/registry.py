from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    scenario_id: str
    code: str
    description: str
    rollback_supported: bool
    injector_method: str


SCENARIO_REGISTRY: dict[str, ScenarioDefinition] = {
    "roce-mtu-mismatch": ScenarioDefinition(
        scenario_id="roce-mtu-mismatch",
        code="RC/F-001",
        description="Inject RoCE MTU mismatch across configured nodes.",
        rollback_supported=True,
        injector_method="inject_roce_mtu_mismatch",
    )
}


def list_scenarios() -> list[ScenarioDefinition]:
    return sorted(SCENARIO_REGISTRY.values(), key=lambda item: item.code)


def get_scenario(scenario_id: str) -> ScenarioDefinition | None:
    return SCENARIO_REGISTRY.get(scenario_id)
