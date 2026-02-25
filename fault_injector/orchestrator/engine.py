from __future__ import annotations

from dataclasses import asdict

from fault_injector.config import InjectorConfig
from fault_injector.injector import FaultInjector
from fault_injector.scenarios.registry import get_scenario


class FaultOrchestrator:
    def __init__(self, config: InjectorConfig) -> None:
        self.config = config

    def run(
        self,
        scenario: str,
        session_id: str,
        only: list[str] | None = None,
        resume: bool = False,
    ) -> dict:
        scenario_def = get_scenario(scenario)
        if scenario_def is None:
            raise ValueError(f"Unknown scenario: {scenario}")

        filtered_cfg = self._filter_config(self.config, only=only or [])
        injector = FaultInjector(config=filtered_cfg, session_id=session_id)

        if resume and scenario_def.rollback_supported:
            injector.rollback()

        action = getattr(injector, scenario_def.injector_method)
        reports = action()
        return {
            "session_id": session_id,
            "scenario": scenario_def.scenario_id,
            "scenario_code": scenario_def.code,
            "resume": resume,
            "targets": [s.name for s in filtered_cfg.servers],
            "reports": [asdict(item) for item in reports],
        }

    @staticmethod
    def _filter_config(config: InjectorConfig, only: list[str]) -> InjectorConfig:
        if not only:
            return config
        target_names = set(only)
        servers = [srv for srv in config.servers if srv.name in target_names]
        return InjectorConfig(
            mode=config.mode,
            wal_path=config.wal_path,
            timeout=config.timeout,
            servers=servers,
        )
