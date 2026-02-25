from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(slots=True)
class ChannelResult:
    """Unified result object returned by all channels."""

    success: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    blocked: bool = False
    dry_run: bool = False
    simulated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


WalHook = Callable[[dict[str, Any]], None]


class BaseChannel(ABC):
    """Base channel with command guardrails + WAL prewrite + dry-run support."""

    _DEFAULT_FORBIDDEN_PATTERNS = (
        re.compile(r"(^|\s)rm\s+-rf\s+/"),
        re.compile(r"(^|\s)mkfs(\.|\s)"),
        re.compile(r"(^|\s)dd\s+if="),
        re.compile(r"(:\(\)\{\s*:\|:\s*&\s*\};:)"),
    )

    def __init__(
        self,
        *,
        dry_run: bool = False,
        wal_hook: WalHook | None = None,
        forbidden_patterns: tuple[re.Pattern[str], ...] | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.wal_hook = wal_hook
        self.forbidden_patterns = forbidden_patterns or self._DEFAULT_FORBIDDEN_PATTERNS

    def _is_forbidden(self, command: str) -> bool:
        cmd = command.strip()
        return any(p.search(cmd) for p in self.forbidden_patterns)

    def execute(
        self,
        command: str,
        *,
        timeout: int = 20,
        wal_payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ChannelResult:
        """Execute command through standard interception pipeline."""
        if self._is_forbidden(command):
            return ChannelResult(
                success=False,
                command=command,
                stderr="Command blocked by security policy",
                returncode=126,
                blocked=True,
            )

        if wal_payload is not None and self.wal_hook is not None:
            try:
                self.wal_hook(wal_payload)
            except Exception as exc:  # noqa: BLE001
                return ChannelResult(
                    success=False,
                    command=command,
                    stderr=f"WAL prewrite failed: {exc}",
                    returncode=1,
                )

        if self.dry_run:
            return ChannelResult(
                success=True,
                command=command,
                stdout="dry-run",
                dry_run=True,
                simulated=True,
            )

        return self._execute_impl(command, timeout=timeout, **kwargs)

    @abstractmethod
    def _execute_impl(self, command: str, *, timeout: int = 20, **kwargs: Any) -> ChannelResult:
        """Channel-specific execution implementation."""

    @staticmethod
    def quote_args(parts: list[str]) -> str:
        """Safely build printable command string with escaped args."""
        return " ".join(shlex.quote(p) for p in parts)


class LocalShellChannel(BaseChannel):
    """Minimal local shell channel for agent probes and command wrappers."""

    def _execute_impl(self, command: str, *, timeout: int = 20, **kwargs: Any) -> ChannelResult:
        proc = subprocess.run(
            ["bash", "-lc", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return ChannelResult(
            success=proc.returncode == 0,
            command=command,
            stdout=proc.stdout,
            stderr=proc.stderr,
            returncode=proc.returncode,
        )


class JsonlWalHook:
    """Simple JSONL WAL writer hook for channel prewrite recording."""

    def __init__(self, wal_path: str) -> None:
        self._path = Path(wal_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, payload: dict[str, Any]) -> None:
        payload = dict(payload)
        payload.setdefault("ts", time.time())
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
