from __future__ import annotations


class SafetyGuard:
    """Very small command guard for obviously dangerous commands."""

    _FORBIDDEN_TOKENS = (
        "rm -rf /",
        "mkfs",
        "dd if=",
        "shutdown",
        "reboot",
    )

    def is_allowed(self, command: str) -> bool:
        normalized = " ".join(command.strip().split()).lower()
        return not any(token in normalized for token in self._FORBIDDEN_TOKENS)
