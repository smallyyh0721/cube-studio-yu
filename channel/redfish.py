from __future__ import annotations

from dataclasses import dataclass

from .base import BaseChannel, ChannelResult


@dataclass(slots=True)
class RedfishTarget:
    base_url: str
    username: str
    password: str


class RedfishChannel(BaseChannel):
    """Placeholder Redfish channel with minimal callable interface."""

    def get(self, target: RedfishTarget, path: str, timeout: int = 10) -> ChannelResult:
        cmd = f"GET {target.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self.execute(cmd, timeout=timeout, target=target)

    def _execute_impl(self, command: str, *, timeout: int = 20, **kwargs) -> ChannelResult:
        return ChannelResult(success=True, command=command, stdout="redfish-placeholder", simulated=True)
