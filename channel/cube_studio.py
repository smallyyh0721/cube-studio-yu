from __future__ import annotations

from .base import BaseChannel, ChannelResult


class CubeStudioChannel(BaseChannel):
    """Placeholder cube-studio channel with minimal endpoint interface."""

    def run_pipeline(self, pipeline_id: str, timeout: int = 30) -> ChannelResult:
        cmd = f"POST /api/v1/pipeline/run pipeline_id={pipeline_id}"
        return self.execute(cmd, timeout=timeout)

    def _execute_impl(self, command: str, *, timeout: int = 20, **kwargs) -> ChannelResult:
        return ChannelResult(success=True, command=command, stdout="cube-studio-placeholder", simulated=True)
