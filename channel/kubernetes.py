from __future__ import annotations

import shlex

from .base import BaseChannel, ChannelResult, LocalShellChannel


class KubernetesChannel(BaseChannel):
    """Minimal kubectl wrapper channel."""

    def __init__(self, *, dry_run: bool = False, wal_hook=None) -> None:
        super().__init__(dry_run=dry_run, wal_hook=wal_hook)
        self._local = LocalShellChannel(dry_run=dry_run, wal_hook=wal_hook)

    def kubectl(self, args: list[str], timeout: int = 20) -> ChannelResult:
        cmd = " ".join(["kubectl", *[shlex.quote(str(a)) for a in args]])
        return self.execute(cmd, timeout=timeout)

    def _execute_impl(self, command: str, *, timeout: int = 20, **kwargs) -> ChannelResult:
        return self._local._execute_impl(command, timeout=timeout, **kwargs)
