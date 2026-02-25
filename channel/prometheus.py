from __future__ import annotations

from .base import BaseChannel, ChannelResult


class PrometheusChannel(BaseChannel):
    """Placeholder Prometheus query channel."""

    def query(self, promql: str, timeout: int = 10) -> ChannelResult:
        cmd = f"GET /api/v1/query?query={promql}"
        return self.execute(cmd, timeout=timeout)

    def _execute_impl(self, command: str, *, timeout: int = 20, **kwargs) -> ChannelResult:
        return ChannelResult(success=True, command=command, stdout="prometheus-placeholder", simulated=True)
