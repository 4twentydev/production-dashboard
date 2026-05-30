from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from collections.abc import Sequence
from pathlib import Path

from .policy import validate_command


@dataclass(frozen=True)
class LaunchResult:
    ok: bool
    message: str
    target: str | None = None
    opened_path: str | None = None
    fallback_path: str | None = None


def _start_process(command: Sequence[str], *, cwd: str | None = None) -> subprocess.Popen[bytes]:
    validate_command(command)
    return subprocess.Popen(
        list(command),
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _run_process(command: Sequence[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    validate_command(command)
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def nearest_existing_parent(path: Path) -> Path | None:
    candidate = path
    while candidate != candidate.parent:
        if candidate.exists():
            return candidate
        candidate = candidate.parent
    return candidate if candidate.exists() else None


def open_path(path: Path) -> LaunchResult:
    if path.exists():
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            _start_process(["open", str(path)])
        else:
            _start_process(["xdg-open", str(path)])
        return LaunchResult(True, f"Opened {path}", target=str(path), opened_path=str(path))

    fallback = nearest_existing_parent(path)
    if fallback is None:
        return LaunchResult(False, f"Missing path and no parent folder exists: {path}", target=str(path))
    if sys.platform.startswith("win"):
        os.startfile(str(fallback))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        _start_process(["open", str(fallback)])
    else:
        _start_process(["xdg-open", str(fallback)])
    return LaunchResult(
        True,
        f"Path missing. Opened nearest existing parent folder: {fallback}",
        target=str(path),
        opened_path=str(fallback),
        fallback_path=str(fallback),
    )


def launch_command(command: Sequence[str], *, cwd: str | None = None) -> LaunchResult:
    _start_process(command, cwd=cwd)
    return LaunchResult(True, f"Launched {' '.join(command)}", target=" ".join(command))


def launch_commands(commands: Sequence[Sequence[str]]) -> LaunchResult:
    launched: list[str] = []
    for command in commands:
        launch_command(command)
        launched.append(" ".join(command))
    return LaunchResult(True, f"Launched {len(launched)} command(s).", target="; ".join(launched))


def run_commands(commands: Sequence[Sequence[str]]) -> LaunchResult:
    outputs: list[str] = []
    for command in commands:
        completed = _run_process(command)
        outputs.append(" ".join(command))
        if completed.stderr.strip():
            outputs.append(completed.stderr.strip())
    return LaunchResult(True, f"Ran {len(commands)} command(s).", target="; ".join(outputs))


def open_url(url: str) -> LaunchResult:
    import webbrowser

    webbrowser.open_new_tab(url)
    return LaunchResult(True, f"Opened {url}", target=url)


def launch_command_setting(command_value: str, *, cwd: str | None = None) -> LaunchResult:
    command_value = command_value.strip()
    if not command_value or command_value == "[]":
        raise ValueError("No command is configured.")
    if command_value.startswith("["):
        command = json.loads(command_value)
    else:
        command = shlex.split(command_value)
    if not isinstance(command, list) or not command:
        raise ValueError("Configured command is invalid.")
    return launch_command([str(part) for part in command], cwd=cwd)


def launch_commands_setting(commands_json: str) -> LaunchResult:
    commands_json = commands_json.strip()
    if not commands_json or commands_json == "[]":
        raise ValueError("No commands are configured.")
    commands = json.loads(commands_json)
    if not isinstance(commands, list) or not commands:
        raise ValueError("Configured commands are invalid.")
    validated: list[list[str]] = []
    for item in commands:
        if not isinstance(item, list) or not item:
            raise ValueError("Each configured mount command must be a non-empty list.")
        validate_command([str(part) for part in item])
        validated.append([str(part) for part in item])
    return launch_commands(validated)


def run_commands_setting(commands_json: str) -> LaunchResult:
    commands_json = commands_json.strip()
    if not commands_json or commands_json == "[]":
        raise ValueError("No commands are configured.")
    commands = json.loads(commands_json)
    if not isinstance(commands, list) or not commands:
        raise ValueError("Configured commands are invalid.")
    validated: list[list[str]] = []
    for item in commands:
        if not isinstance(item, list) or not item:
            raise ValueError("Each configured command must be a non-empty list.")
        validate_command([str(part) for part in item])
        validated.append([str(part) for part in item])
    return run_commands(validated)
