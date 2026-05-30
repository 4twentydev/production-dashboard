from __future__ import annotations

from collections.abc import Sequence

BLOCKED_TOKENS = {
    "rm",
    "rmdir",
    "del",
    "erase",
    "format",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
    "poweroff",
    "halt",
    "kill",
    "killall",
    "taskkill",
}


def command_looks_destructive(command: Sequence[str]) -> bool:
    return any(token.strip().lower() in BLOCKED_TOKENS for token in command)


def validate_command(command: Sequence[str]) -> None:
    if not command:
        raise ValueError("Command is empty.")
    if command_looks_destructive(command):
        raise PermissionError("Destructive commands are blocked.")

