from __future__ import annotations

import asyncio
import re
import shlex
from dataclasses import dataclass

from .base import BaseChannel, ChannelResult


@dataclass(slots=True)
class HostSpec:
    name: str
    host: str
    user: str
    port: int = 22
    password: str | None = None


class AsyncSSHConnectionPool:
    """Async SSH execution pool controlled via semaphore."""

    def __init__(self, max_connections: int = 8) -> None:
        self._sem = asyncio.Semaphore(max_connections)

    async def run(self, host_spec: HostSpec, remote_command: str, timeout: int = 20) -> ChannelResult:
        target = f"{host_spec.user}@{host_spec.host}"
        cmd = ["ssh", "-p", str(host_spec.port), target, remote_command]
        rendered = BaseChannel.quote_args(cmd)
        async with self._sem:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return ChannelResult(
                    success=False,
                    command=rendered,
                    stderr=f"SSH timeout after {timeout}s",
                    returncode=124,
                )
        return ChannelResult(
            success=proc.returncode == 0,
            command=rendered,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=int(proc.returncode or 0),
        )


class SSHChannel(BaseChannel):
    """SSH command channel with simulation mode and pooled async execution."""

    _MTU_PATTERN = re.compile(r"ip link set dev (?P<iface>\S+) mtu (?P<mtu>\d+)")

    def __init__(
        self,
        mode: str = "simulate",
        *,
        dry_run: bool = False,
        wal_hook=None,
        max_connections: int = 8,
    ) -> None:
        if mode not in {"simulate", "ssh"}:
            raise ValueError("mode must be simulate or ssh")
        super().__init__(dry_run=dry_run, wal_hook=wal_hook)
        self.mode = mode
        self._pool = AsyncSSHConnectionPool(max_connections=max_connections)
        self._simulated_mtu: dict[tuple[str, str], int] = {}

    def seed_simulated_mtu(self, host: str, interface: str, mtu: int) -> None:
        self._simulated_mtu[(host, interface)] = mtu

    def get_simulated_mtu(self, host: str, interface: str) -> int | None:
        return self._simulated_mtu.get((host, interface))

    def execute(
        self,
        host_spec: HostSpec,
        remote_command: str,
        timeout: int = 20,
        *,
        wal_payload: dict | None = None,
    ) -> ChannelResult:
        return super().execute(
            remote_command,
            timeout=timeout,
            wal_payload=wal_payload,
            host_spec=host_spec,
        )

    def _execute_impl(self, command: str, *, timeout: int = 20, **kwargs) -> ChannelResult:
        host_spec: HostSpec = kwargs["host_spec"]
        if self.mode == "simulate":
            return self._simulate_execute(host_spec, command)
        return asyncio.run(self._pool.run(host_spec, command, timeout=timeout))

    def _simulate_execute(self, host_spec: HostSpec, remote_command: str) -> ChannelResult:
        match = self._MTU_PATTERN.search(remote_command)
        if match:
            iface = shlex.split(match.group("iface"))[0]
            mtu = int(match.group("mtu"))
            self._simulated_mtu[(host_spec.name, iface)] = mtu
        return ChannelResult(
            success=True,
            command=remote_command,
            stdout="simulated",
            simulated=True,
        )
