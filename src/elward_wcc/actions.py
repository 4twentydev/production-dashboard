from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path

from . import backups, browser, db, launcher, notes, security
from .config import DEFAULT_SETTINGS, ELWARD_URLS, MOUNT_PATHS
from .models import ActionResult, ActionSpec

ACTION_SPECS: tuple[ActionSpec, ...] = (
    ActionSpec("open_release_docs", "Open Release Docs", "folder", "release_docs_path"),
    ActionSpec("open_drawings", "Open Drawings", "folder", "drawings_path"),
    ActionSpec("open_cnc_files", "Open CNC Files", "folder", "cnc_files_path"),
    ActionSpec("open_pallet_tracker", "Open Pallet Tracker", "url", "pallet_tracker_url"),
    ActionSpec("open_all_releases", "Open All Releases", "url", "all_releases_url"),
    ActionSpec("open_browser_tabs", "Open Useful Browser Tabs", "internal_action", "browser_tab_urls"),
    ActionSpec("mount_shares", "Mount Elward Shares", "internal_action", "mount_commands_json", requires_pin=True),
    ActionSpec("open_wireguard", "Open WireGuard", "shell", "wireguard_command", requires_pin=True),
    ActionSpec("launch_autocad", "Launch AutoCAD", "app", "autocad_command", requires_pin=True),
    ActionSpec("refresh_job_index", "Refresh Job Index", "internal_action", "jobs", requires_pin=True),
    ActionSpec("backup_database", "Backup Command Center DB", "internal_action", "db", requires_pin=True),
    ActionSpec("create_blank_release_checklist", "Create Blank Release Checklist", "template", "blank_release_checklist"),
    ActionSpec("generate_material_shortage_note", "Generate Material Shortage Note", "template", "material_shortage_note"),
    ActionSpec("generate_daily_production_summary", "Generate Daily Production Summary", "template", "daily_production_summary"),
)


def ensure_registry() -> None:
    for spec in ACTION_SPECS:
        db.upsert_action(
            {
                "key": spec.key,
                "label": spec.label,
                "kind": spec.kind,
                "target": spec.target,
                "args_json": spec.args_json,
                "platform": spec.platform,
                "requires_pin": spec.requires_pin,
                "destructive": spec.destructive,
                "enabled": spec.enabled,
            }
        )


def list_actions() -> list[dict[str, object]]:
    return db.list_actions()


def _safe_details(action_key: str, payload: dict[str, str] | None) -> dict[str, object]:
    if not payload:
        return {}
    if action_key.startswith("generate_") or action_key == "create_blank_release_checklist":
        return {"payload_keys": sorted(payload.keys()), "payload_count": len(payload)}
    return {"payload_keys": sorted(payload.keys()), "payload_count": len(payload)}


def _resolve_setting(setting_key: str, default: str = "") -> str:
    value = db.get_setting(setting_key, default)
    return default if value is None else value


def _dispatch(spec: ActionSpec, payload: dict[str, str] | None = None) -> str:
    if spec.kind == "folder":
        raw = _resolve_setting(spec.target)
        if not raw.strip():
            raise ValueError(f"No path is configured for {spec.label}.")
        result = launcher.open_path(Path(raw))
        return result.message
    if spec.kind == "url":
        url = _resolve_setting(spec.target)
        if not url.strip():
            raise ValueError(f"No URL is configured for {spec.label}.")
        result = browser.open_url(url)
        return result.message
    if spec.kind == "internal_action" and spec.key == "open_browser_tabs":
        raw = _resolve_setting(spec.target, "[]")
        urls = json.loads(raw or "[]")
        if not isinstance(urls, list):
            raise ValueError("Browser tabs setting must be a JSON list.")
        result = browser.open_tabs([str(url) for url in urls])
        return result.message
    if spec.kind in {"app", "shell"}:
        command_value = _resolve_setting(spec.target, "[]")
        result = launcher.launch_command_setting(command_value)
        return result.message
    if spec.kind == "internal_action" and spec.key == "mount_shares":
        commands_value = _resolve_setting(spec.target, "[]")
        result = launcher.run_commands_setting(commands_value)
        return result.message
    if spec.kind == "internal_action" and spec.key == "refresh_job_index":
        from .jobs import refresh_job_index

        result = refresh_job_index()
        return f"Refreshed {result['jobs_scanned']} indexed item(s)."
    if spec.kind == "internal_action" and spec.key == "backup_database":
        path = backups.backup_database()
        return f"Backup created at {path}"
    if spec.kind == "template":
        if spec.key == "create_blank_release_checklist":
            title, _ = notes.blank_release_checklist(
                job_ref=(payload or {}).get("job_ref", ""),
                release_ref=(payload or {}).get("release_ref", ""),
            )
            return f"Created note: {title}"
        if spec.key == "generate_material_shortage_note":
            title, _ = notes.material_shortage_note(
                job_ref=(payload or {}).get("job_ref", ""),
                release_ref=(payload or {}).get("release_ref", ""),
                material=(payload or {}).get("material", ""),
                quantity_needed=(payload or {}).get("quantity_needed", ""),
                shortage=(payload or {}).get("shortage", ""),
                needed_by_date=(payload or {}).get("needed_by_date", ""),
                notes_text=(payload or {}).get("notes_text", ""),
                requested_by=(payload or {}).get("requested_by", ""),
            )
            return f"Created note: {title}"
        if spec.key == "generate_daily_production_summary":
            title, _ = notes.daily_production_summary(
                summary_date=None,
                releases_worked=(payload or {}).get("releases_worked", ""),
                panels_completed=(payload or {}).get("panels_completed", ""),
                pallets_completed=(payload or {}).get("pallets_completed", ""),
                cnc_status=(payload or {}).get("cnc_status", ""),
                assembly_status=(payload or {}).get("assembly_status", ""),
                shipping_status=(payload or {}).get("shipping_status", ""),
                blockers=(payload or {}).get("blockers", ""),
                next_steps=(payload or {}).get("next_steps", ""),
                notes_text=(payload or {}).get("notes_text", ""),
            )
            return f"Created note: {title}"
    raise ValueError(f"Unsupported action kind: {spec.kind}")


def execute_action(
    action_key: str,
    *,
    storage: MutableMapping[str, object],
    payload: dict[str, str] | None = None,
) -> ActionResult:
    spec = next((item for item in ACTION_SPECS if item.key == action_key), None)
    if spec is None:
        db.log_action(action_key, allowed=False, success=False, message="Unknown action.")
        return ActionResult(False, "Unknown action.")
    if not spec.enabled:
        db.log_action(action_key, allowed=False, success=False, message="Action is disabled.")
        return ActionResult(False, "Action is disabled.")
    if spec.requires_pin and not security.is_unlocked(storage):
        db.log_action(action_key, allowed=False, success=False, message=security.pin_required_message())
        return ActionResult(False, security.pin_required_message())
    try:
        result = _dispatch(spec, payload)
        db.log_action(action_key, allowed=True, success=True, message=result, details=_safe_details(action_key, payload))
        return ActionResult(True, result)
    except Exception as exc:  # noqa: BLE001
        db.log_action(action_key, allowed=True, success=False, message=str(exc), details=_safe_details(action_key, payload))
        return ActionResult(False, str(exc))


def seeded_defaults() -> dict[str, str]:
    return {
        "release_docs_path": str(MOUNT_PATHS["release_docs"]),
        "drawings_path": str(MOUNT_PATHS["drawings"]),
        "cnc_files_path": str(MOUNT_PATHS["cnc_files"]),
        "pallet_tracker_url": ELWARD_URLS["pallet_tracker"],
        "all_releases_url": ELWARD_URLS["all_releases"],
        "mount_commands_json": DEFAULT_SETTINGS["mount_commands_json"],
        "browser_tab_urls": DEFAULT_SETTINGS["browser_tab_urls"],
    }
