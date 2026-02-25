from __future__ import annotations

from dataclasses import dataclass

from .base import BaseChannel, ChannelResult


@dataclass(slots=True)
class SwitchTarget:
    host: str
    username: str
    password: str


class SwitchChannel(BaseChannel):
    """Placeholder network-switch channel with minimal command API."""

    def run_cli(self, target: SwitchTarget, cli_command: str, timeout: int = 20) -> ChannelResult:
        return self.execute(cli_command, timeout=timeout, target=target)

    def _execute_impl(self, command: str, *, timeout: int = 20, **kwargs) -> ChannelResult:
        return ChannelResult(success=True, command=command, stdout="switch-placeholder", simulated=True)
