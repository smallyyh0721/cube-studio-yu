from __future__ import annotations

from collections.abc import Callable


class ScenarioRegistry:
    def __init__(self) -> None:
        self._scenarios: dict[str, Callable[[], object]] = {}

    def register(self, name: str, handler: Callable[[], object]) -> None:
        if name in self._scenarios:
            raise ValueError(f"Scenario already registered: {name}")
        self._scenarios[name] = handler

    def get(self, name: str) -> Callable[[], object]:
        if name not in self._scenarios:
            raise KeyError(name)
        return self._scenarios[name]

    def list(self) -> list[str]:
        return sorted(self._scenarios)
