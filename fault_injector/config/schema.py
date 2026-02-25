from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServerConfigModel(BaseModel):
    name: str = Field(min_length=1)
    host: str = Field(min_length=1)
    user: str = Field(min_length=1)
    port: int = Field(default=22, ge=1, le=65535)
    interface: str = Field(min_length=1)
    original_mtu: int = Field(ge=576, le=9700)
    fault_mtu: int = Field(ge=576, le=9700)


class InjectorSection(BaseModel):
    mode: Literal["simulate", "ssh"] = "simulate"
    wal_path: str = Field(default="fault_injector/rollback.wal", min_length=1)
    timeout: int = Field(default=20, ge=1, le=600)


class ChannelSection(BaseModel):
    connect_timeout: int = Field(default=10, ge=1, le=300)
    command_timeout: int = Field(default=20, ge=1, le=3600)
    retries: int = Field(default=0, ge=0, le=5)


class SafetySection(BaseModel):
    dry_run: bool = False
    require_root: bool = True
    max_parallel_hosts: int = Field(default=8, ge=1, le=128)


class ScenarioSection(BaseModel):
    name: Literal["roce_mtu_mismatch"] = "roce_mtu_mismatch"
    servers: list[ServerConfigModel] = Field(default_factory=list, min_length=1)


class ReportingSection(BaseModel):
    format: Literal["json", "text"] = "json"
    output_path: str = Field(default="fault_injector/report.json", min_length=1)
    include_commands: bool = True


class FaultInjectorConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    injector: InjectorSection = Field(default_factory=InjectorSection)
    channel: ChannelSection = Field(default_factory=ChannelSection)
    safety: SafetySection = Field(default_factory=SafetySection)
    scenario: ScenarioSection = Field(default_factory=ScenarioSection)
    reporting: ReportingSection = Field(default_factory=ReportingSection)

    @model_validator(mode="before")
    @classmethod
    def _adapt_legacy_servers_layout(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        servers = payload.pop("servers", None)

        if servers is not None and "scenario" not in payload:
            payload["scenario"] = {"servers": servers}
        elif servers is not None and isinstance(payload.get("scenario"), dict):
            scenario = dict(payload["scenario"])
            scenario.setdefault("servers", servers)
            payload["scenario"] = scenario

        return payload
