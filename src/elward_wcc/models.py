from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionSpec:
    key: str
    label: str
    kind: str
    target: str
    args_json: str = "[]"
    platform: str = "any"
    requires_pin: bool = False
    destructive: bool = False
    enabled: bool = True


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

