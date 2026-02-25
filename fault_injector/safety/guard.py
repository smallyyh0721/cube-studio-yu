from __future__ import annotations

import re
from dataclasses import dataclass, field


class SafetyViolationError(RuntimeError):
    """Raised when an operation fails safety pre-checks."""


@dataclass(slots=True)
class SafetyGuard:
    """Validate targets and commands before execution."""

    authorized_targets: set[str]
    forbidden_namespaces: set[str] = field(default_factory=lambda: {"prod", "production", "kube-system"})
    dangerous_command_patterns: tuple[re.Pattern[str], ...] = field(
        default_factory=lambda: (
            re.compile(r"\brm\s+-rf\s+/"),
            re.compile(r"\bmkfs(\.|\s)"),
            re.compile(r"\bdd\s+if=.*\sof="),
            re.compile(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;"),
        )
    )

    def validate(self, target: str, command: str, namespace: str | None = None) -> None:
        self._validate_target(target)
        self._validate_namespace(namespace or target)
        self._validate_command(command)

    def _validate_target(self, target: str) -> None:
        if target not in self.authorized_targets:
            raise SafetyViolationError(f"Target `{target}` is not authorized.")

    def _validate_namespace(self, namespace: str) -> None:
        lower_ns = namespace.lower()
        if any(flag in lower_ns for flag in self.forbidden_namespaces):
            raise SafetyViolationError(f"Namespace/target `{namespace}` is blocked by safety rules.")

    def _validate_command(self, command: str) -> None:
        for pattern in self.dangerous_command_patterns:
            if pattern.search(command):
                raise SafetyViolationError(f"Dangerous command blocked by guard: `{command}`")
