from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi.responses import JSONResponse, Response
from nicegui import app, ui

from . import actions, db, notes, security
from .config import APP_NAME, APP_VERSION, DEFAULT_SETTINGS, MOUNT_PATHS, SMB_PATHS
from .jobs import recent_jobs, refresh_job_index, search_jobs
from .launcher import nearest_existing_parent, open_path

PIN_DIALOG: ui.dialog | None = None
SETTINGS_DIALOG: ui.dialog | None = None
SEARCH_INPUT: ui.input | None = None


def _setting(key: str, default: str = "") -> str:
    value = db.get_setting(key, default)
    return default if value is None else value


def _json_list_setting(key: str, default: str = "[]") -> list[Any]:
    raw = _setting(key, default)
    try:
        value = json.loads(raw or default)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _open_result_for_path(path_str: str) -> tuple[bool, str, str | None]:
    path = Path(path_str)
    if path.exists():
        result = open_path(path)
        return result.ok, result.message, result.fallback_path
    fallback = nearest_existing_parent(path)
    if fallback is None:
        return False, f"Missing path and no existing parent folder was found: {path}", None
    result = open_path(fallback)
    return True, f"{path} is missing. Opened nearest existing parent folder: {fallback}", str(fallback)


def _notify_path_open(path_str: str) -> None:
    ok, message, _ = _open_result_for_path(path_str)
    ui.notify(message, color="positive" if ok else "negative")


def _status_color(present: bool, is_mount: bool) -> str:
    if not present:
        return "negative"
    return "positive" if is_mount else "warning"


def _current_unlock_minutes() -> int:
    try:
        return int(_setting("pin_unlock_minutes", DEFAULT_SETTINGS["pin_unlock_minutes"]))
    except ValueError:
        return int(DEFAULT_SETTINGS["pin_unlock_minutes"])


def _dashboard_urls() -> list[str]:
    urls: list[str] = []
    dashboard_url = _setting("dashboard_url", "")
    dashboard_url_local = _setting("dashboard_url_local", "")
    if dashboard_url:
        urls.append(dashboard_url)
    if dashboard_url_local and dashboard_url_local != dashboard_url:
        urls.append(dashboard_url_local)
    if not urls:
        port = _setting("resolved_port", _setting("app_port", DEFAULT_SETTINGS["app_port"]))
        host = _setting("resolved_host", _setting("app_host", DEFAULT_SETTINGS["app_host"]))
        if host == "0.0.0.0":
            urls.append(f"http://{host}:{port}")
            urls.append(f"http://127.0.0.1:{port}")
        else:
            urls.append(f"http://{host}:{port}")
    return urls


def _pending_action() -> dict[str, Any] | None:
    value = app.storage.user.get("pending_action")
    return value if isinstance(value, dict) else None


def _clear_pending() -> None:
    app.storage.user.pop("pending_action", None)
    app.storage.user.pop("pending_ui_target", None)


def _run_action(action_key: str, *, payload: dict[str, str] | None = None) -> None:
    spec = next((item for item in actions.ACTION_SPECS if item.key == action_key), None)
    if spec is None:
        ui.notify("Unknown action.", color="negative")
        return
    if spec.requires_pin and not security.is_unlocked(app.storage.user):
        app.storage.user["pending_action"] = {"key": action_key, "payload": payload or {}}
        if PIN_DIALOG is not None:
            PIN_DIALOG.open()
        ui.notify("PIN required.", color="warning")
        return
    result = actions.execute_action(action_key, storage=app.storage.user, payload=payload)
    if result.ok:
        ui.notify(result.message, color="positive")
    else:
        ui.notify(result.message, color="negative")


def _request_settings() -> None:
    if security.is_unlocked(app.storage.user):
        if SETTINGS_DIALOG is not None:
            SETTINGS_DIALOG.open()
        return
    app.storage.user["pending_ui_target"] = "settings"
    if PIN_DIALOG is not None:
        PIN_DIALOG.open()
    ui.notify("PIN required for settings.", color="warning")


def _render_pin_dialog() -> ui.dialog:
    dialog = ui.dialog()
    with dialog:
        with ui.card().classes("w-[360px] max-w-full bg-slate-900 text-slate-100"):
            ui.label("Unlock protected sections").classes("text-lg font-semibold")
            pin_input = ui.input("PIN", password=True, password_toggle_button=True).classes("w-full")
            message = ui.label("").classes("text-sm text-amber-300")

            def submit_pin() -> None:
                pin = (pin_input.value or "").strip()
                if not security.is_pin_configured():
                    if not pin:
                        message.text = "Enter a new PIN to initialize protected sections."
                        return
                    security.set_pin(pin)
                    security.register_unlock(app.storage.user, minutes=_current_unlock_minutes())
                    message.text = ""
                    ui.notify("PIN created and unlocked.", color="positive")
                else:
                    if not security.verify_pin(pin):
                        message.text = "Invalid PIN."
                        ui.notify("Invalid PIN.", color="negative")
                        return
                    security.register_unlock(app.storage.user, minutes=_current_unlock_minutes())
                    message.text = ""
                    ui.notify("Unlocked.", color="positive")
                dialog.close()
                target = app.storage.user.pop("pending_ui_target", None)
                pending_action = _pending_action()
                _clear_pending()
                if target == "settings" and SETTINGS_DIALOG is not None:
                    SETTINGS_DIALOG.open()
                elif pending_action:
                    _run_action(
                        str(pending_action.get("key", "")),
                        payload=pending_action.get("payload") if isinstance(pending_action.get("payload"), dict) else None,
                    )

            with ui.row().classes("gap-2"):
                ui.button("Unlock", on_click=submit_pin).props("unelevated color=primary")
                ui.button("Cancel", on_click=dialog.close).props("flat")
    return dialog


def _render_settings_dialog() -> ui.dialog:
    dialog = ui.dialog()
    with dialog:
        with ui.card().classes("w-[980px] max-w-[96vw] bg-slate-900 text-slate-100"):
            ui.label("Protected Settings").classes("text-xl font-semibold")
            ui.label("Settings are local to the Zorin host. SMB passwords are not stored here.")

            network_mode = ui.select(
                ["lan", "local", "custom"],
                value=_setting("network_mode", DEFAULT_SETTINGS["network_mode"]),
                label="Network behavior",
            )
            app_host = ui.input("App host", value=_setting("app_host", DEFAULT_SETTINGS["app_host"]))
            app_port = ui.input("App port", value=_setting("app_port", DEFAULT_SETTINGS["app_port"]))
            native_window = ui.switch("Native window on host", value=_setting("native_window", "0") == "1")
            backup_dir = ui.input("Backup folder", value=_setting("backup_dir", DEFAULT_SETTINGS["backup_dir"]))

            with ui.row().classes("w-full gap-4"):
                release_docs_path = ui.input("Release Docs local path", value=_setting("release_docs_path", DEFAULT_SETTINGS["release_docs_path"]))
                drawings_path = ui.input("Drawings local path", value=_setting("drawings_path", DEFAULT_SETTINGS["drawings_path"]))
                cnc_files_path = ui.input("CNC Files local path", value=_setting("cnc_files_path", DEFAULT_SETTINGS["cnc_files_path"]))

            with ui.row().classes("w-full gap-4"):
                release_docs_smb = ui.input("Release Docs SMB path", value=_setting("release_docs_smb_path", SMB_PATHS["release_docs"]))
                drawings_smb = ui.input("Drawings SMB path", value=_setting("drawings_smb_path", SMB_PATHS["drawings"]))
                cnc_files_smb = ui.input("CNC Files SMB path", value=_setting("cnc_files_smb_path", SMB_PATHS["cnc_files"]))

            browser_tabs = ui.textarea("Useful browser tabs JSON list", value=_setting("browser_tab_urls", DEFAULT_SETTINGS["browser_tab_urls"]))
            autocad_command = ui.textarea("AutoCAD command JSON list", value=_setting("autocad_command", DEFAULT_SETTINGS["autocad_command"]))
            wireguard_command = ui.textarea("WireGuard command JSON list", value=_setting("wireguard_command", DEFAULT_SETTINGS["wireguard_command"]))
            mount_commands_json = ui.textarea("Mount Elward Shares commands JSON list", value=_setting("mount_commands_json", DEFAULT_SETTINGS["mount_commands_json"]))
            unlock_minutes = ui.input("PIN unlock minutes", value=_setting("pin_unlock_minutes", DEFAULT_SETTINGS["pin_unlock_minutes"]))
            lockout_minutes = ui.input("PIN lockout minutes", value=_setting("pin_lockout_minutes", DEFAULT_SETTINGS["pin_lockout_minutes"]))

            def save_settings() -> None:
                db.set_setting("network_mode", str(network_mode.value or "lan"), protected=True)
                db.set_setting("app_host", str(app_host.value or "0.0.0.0"), protected=True)
                db.set_setting("app_port", str(app_port.value or "8080"), protected=True)
                db.set_setting("native_window", "1" if native_window.value else "0", protected=True)
                db.set_setting("backup_dir", str(backup_dir.value or DEFAULT_SETTINGS["backup_dir"]), protected=True)
                db.set_setting("release_docs_path", str(release_docs_path.value or DEFAULT_SETTINGS["release_docs_path"]), protected=True)
                db.set_setting("drawings_path", str(drawings_path.value or DEFAULT_SETTINGS["drawings_path"]), protected=True)
                db.set_setting("cnc_files_path", str(cnc_files_path.value or DEFAULT_SETTINGS["cnc_files_path"]), protected=True)
                db.set_setting("release_docs_smb_path", str(release_docs_smb.value or SMB_PATHS["release_docs"]), protected=True)
                db.set_setting("drawings_smb_path", str(drawings_smb.value or SMB_PATHS["drawings"]), protected=True)
                db.set_setting("cnc_files_smb_path", str(cnc_files_smb.value or SMB_PATHS["cnc_files"]), protected=True)
                db.set_setting("browser_tab_urls", str(browser_tabs.value or "[]"), protected=True)
                db.set_setting("autocad_command", str(autocad_command.value or "[]"), protected=True)
                db.set_setting("wireguard_command", str(wireguard_command.value or "[]"), protected=True)
                db.set_setting("mount_commands_json", str(mount_commands_json.value or "[]"), protected=True)
                db.set_setting("pin_unlock_minutes", str(unlock_minutes.value or "480"), protected=True)
                db.set_setting("pin_lockout_minutes", str(lockout_minutes.value or "10"), protected=True)
                ui.notify("Settings saved.", color="positive")
                dialog.close()

            with ui.row().classes("gap-2"):
                ui.button("Save", on_click=save_settings).props("unelevated color=primary")
                ui.button("Close", on_click=dialog.close).props("flat")
    return dialog


def _folder_status_card(label: str, path_setting: str, fallback_smb: str) -> None:
    raw_path = _setting(path_setting, "")
    path = Path(raw_path) if raw_path else None
    exists = bool(path and path.exists())
    fallback = nearest_existing_parent(path) if path else None
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label(label).classes("text-lg font-semibold")
        ui.label(raw_path or "Not configured").classes("text-sm text-slate-300")
        ui.label(f"SMB reference: {fallback_smb}").classes("text-xs text-slate-400")
        if exists:
            ui.badge("Mounted / available", color="positive")
            ui.button("Open", on_click=lambda p=path: _notify_path_open(str(p))).props("unelevated color=primary").classes("w-full min-h-[52px]")
        elif fallback is not None:
            ui.badge("Missing mount", color="warning")
            ui.label(f"Nearest existing parent: {fallback}").classes("text-xs text-amber-200")
            ui.button("Open parent", on_click=lambda p=fallback: _notify_path_open(str(p))).props("unelevated color=warning").classes("w-full min-h-[52px]")
        else:
            ui.badge("Missing mount", color="negative")
            ui.label("No existing parent folder was found. Run Mount Elward Shares first.").classes("text-xs text-red-200")


def _action_card(action_key: str) -> None:
    spec = next(item for item in actions.ACTION_SPECS if item.key == action_key)
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label(spec.label).classes("text-lg font-semibold")
        if spec.requires_pin:
            ui.badge("PIN required", color="warning")
        ui.button("Run", on_click=lambda key=action_key: _run_action(key)).props("unelevated color=primary").classes("w-full min-h-[52px]")


def _render_action_cards() -> None:
    with ui.element("div").classes("w-full grid grid-cols-1 md:grid-cols-2 gap-3"):
        for key in [
            "open_release_docs",
            "open_drawings",
            "open_cnc_files",
            "open_pallet_tracker",
            "open_all_releases",
            "launch_autocad",
            "mount_shares",
            "refresh_job_index",
            "backup_database",
            "create_blank_release_checklist",
        ]:
            _action_card(key)


def _render_job_results(results: list[dict[str, Any]], container: ui.column) -> None:
    container.clear()
    with container:
        if not results:
            ui.label("No jobs found. Refresh the job index or try a shorter query.")
            return
        for job in results:
            source_path = str(job.get("source_path") or "")
            path = Path(source_path) if source_path else None
            exists = bool(path and path.exists())
            fallback = nearest_existing_parent(path) if path else None
            with ui.card().classes("w-full bg-slate-900 text-slate-100"):
                title_bits = [job.get("job_number"), job.get("release_code"), job.get("pallet_code")]
                title = " ".join(bit for bit in title_bits if bit) or str(job.get("display_name") or "Job")
                ui.label(title).classes("text-lg font-semibold")
                ui.label(str(job.get("display_name") or "")).classes("text-sm text-slate-300")
                detail_bits = [
                    f"Mark {job['mark_number']}" if job.get("mark_number") else "",
                    str(job.get("source_type") or ""),
                    source_path,
                ]
                ui.label(" | ".join(bit for bit in detail_bits if bit)).classes("text-xs text-slate-400")
                with ui.row().classes("gap-2"):
                    if source_path:
                        if exists:
                            ui.button("Open Source", on_click=lambda p=source_path: _notify_path_open(p)).props("unelevated color=primary")
                        elif fallback is not None:
                            ui.button("Open Parent", on_click=lambda p=str(fallback): _notify_path_open(p)).props("unelevated color=warning")
                    if job.get("id") is not None:
                        ui.button(
                            "Pin Job",
                            on_click=lambda job_id=job["id"], label=title: _pin_job(int(job_id), label),
                        ).props("flat")


def _pin_job(job_id: int, label: str) -> None:
    db.set_pinned_job(job_id, label)
    ui.notify(f"Pinned {label}.", color="positive")


def _unpin_job() -> None:
    db.clear_pinned_job()
    ui.notify("Pinned job cleared.", color="positive")


def _render_pinned_job_card() -> None:
    pinned = db.get_pinned_job()
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label("Pinned Job").classes("text-xl font-semibold")
        if not pinned or not pinned.get("display_name"):
            ui.label("No pinned job. Pin one from search or recent jobs.")
            return
        title_bits = [pinned.get("job_number"), pinned.get("release_code"), pinned.get("pallet_code")]
        ui.label(" ".join(bit for bit in title_bits if bit) or str(pinned.get("display_name"))).classes("text-lg font-semibold")
        ui.label(str(pinned.get("display_name") or "")).classes("text-sm text-slate-300")
        source_path = str(pinned.get("source_path") or "")
        if source_path:
            path = Path(source_path)
            if path.exists():
                ui.button("Open Source", on_click=lambda p=source_path: _notify_path_open(p)).props("unelevated color=primary").classes("min-h-[52px]")
            else:
                fallback = nearest_existing_parent(path)
                ui.label(f"Missing path: {source_path}").classes("text-xs text-amber-200")
                if fallback is not None:
                    ui.button("Open Parent", on_click=lambda p=str(fallback): _notify_path_open(p)).props("unelevated color=warning").classes("min-h-[52px]")
        with ui.row().classes("gap-2"):
            ui.button("Unpin", on_click=_unpin_job).props("flat").classes("min-h-[48px]")
            ui.button("Search this job", on_click=lambda: _set_search_query(str(title_bits[0] or ""))).props("flat").classes("min-h-[48px]")


def _set_search_query(query: str) -> None:
    if SEARCH_INPUT is not None:
        SEARCH_INPUT.value = query


def _render_recent_jobs_card() -> None:
    jobs = recent_jobs(limit=8)
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label("Recent Jobs").classes("text-xl font-semibold")
        if not jobs:
            ui.label("No indexed jobs yet.")
            return
        for job in jobs[:8]:
            ui.separator()
            title = " ".join(
                bit for bit in [job.get("job_number"), job.get("release_code"), job.get("pallet_code")] if bit
            ) or str(job.get("display_name") or "Job")
            with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label(title).classes("font-semibold")
                    ui.label(str(job.get("display_name") or "")).classes("text-xs text-slate-400")
                with ui.row().classes("gap-2 flex-wrap"):
                    if job.get("id") is not None:
                        ui.button(
                            "Pin",
                            on_click=lambda job_id=job["id"], label=title: _pin_job(int(job_id), label),
                        ).props("flat").classes("min-h-[48px]")
                    source_path = str(job.get("source_path") or "")
                    if source_path:
                        ui.button("Open", on_click=lambda p=source_path: _notify_path_open(p)).props("flat").classes("min-h-[48px]")


def _render_search_card() -> None:
    global SEARCH_INPUT
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label("Job Search").classes("text-xl font-semibold")
        SEARCH_INPUT = ui.input("Search jobs, releases, pallets, marks, file names").props("clearable").classes("w-full")
        with ui.row().classes("gap-2 flex-wrap"):
            ui.button("Search", on_click=_run_search).props("unelevated color=primary").classes("min-h-[52px] px-5")
            ui.button("Refresh Job Index", on_click=lambda: _run_action("refresh_job_index")).props("unelevated color=secondary").classes("min-h-[52px] px-5")
        searches = db.list_recent_searches(limit=8)
        if searches:
            ui.label("Recent searches").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2 flex-wrap"):
                for item in searches:
                    query = str(item["query"])
                    ui.button(
                        f'{query} ({item["results_count"]})',
                        on_click=lambda q=query: _set_search_query(q),
                    ).props("flat").classes("min-h-[44px]")
        global SEARCH_RESULTS
        SEARCH_RESULTS = ui.column().classes("w-full gap-3")
        _render_job_results(recent_jobs(limit=6), SEARCH_RESULTS)


def _run_search() -> None:
    if SEARCH_INPUT is None or SEARCH_RESULTS is None:
        return
    query = str(SEARCH_INPUT.value or "").strip()
    results = search_jobs(query)
    _render_job_results(results, SEARCH_RESULTS)


SEARCH_RESULTS: ui.column | None = None

MANIFEST = {
    "name": "Elward Command Center",
    "short_name": "Elward Command Center",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#020617",
    "theme_color": "#0f172a",
    "icons": [],
}

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="96" fill="#0f172a"/>
<path d="M120 160h272v64H120zm0 96h208v64H120zm0 96h160v32H120z" fill="#e2e8f0"/>
<circle cx="368" cy="352" r="28" fill="#38bdf8"/>
</svg>"""


@app.get("/manifest.json")
@app.get("/manifest.webmanifest")
def manifest() -> JSONResponse:
    return JSONResponse(MANIFEST)


@app.get("/elward-icon.svg")
def icon() -> Response:
    return Response(content=ICON_SVG, media_type="image/svg+xml")


def _render_templates_card() -> None:
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label("Templates").classes("text-xl font-semibold")
        with ui.tabs().classes("w-full") as tabs:
            blank_tab = ui.tab("Blank Checklist")
            shortage_tab = ui.tab("Material Shortage Note")
            summary_tab = ui.tab("Daily Production Summary")
        with ui.tab_panels(tabs, value=blank_tab).classes("w-full bg-transparent"):
            with ui.tab_panel(blank_tab):
                job_ref = ui.input("Job number / reference")
                release_ref = ui.input("Release")
                output = ui.textarea("Generated note").props("readonly").classes("w-full")

                def generate() -> None:
                    title, body = notes.blank_release_checklist(
                        job_ref=str(job_ref.value or ""),
                        release_ref=str(release_ref.value or ""),
                    )
                    output.value = f"{title}\n\n{body}"
                    ui.notify("Blank release checklist created.", color="positive")

                ui.button("Create Blank Release Checklist", on_click=generate).props("unelevated color=primary")
            with ui.tab_panel(shortage_tab):
                fields = {
                    "job_number": ui.input("Job number"),
                    "release": ui.input("Release"),
                    "material": ui.input("Material"),
                    "quantity_needed": ui.input("Quantity needed"),
                    "issue_blocker": ui.textarea("Issue / blocker"),
                    "needed_by_date": ui.input("Needed by date"),
                    "notes": ui.textarea("Notes"),
                }
                output = ui.textarea("Generated note").props("readonly").classes("w-full")

                def generate_shortage() -> None:
                    title, body = notes.material_shortage_note(
                        job_ref=str(fields["job_number"].value or ""),
                        release_ref=str(fields["release"].value or ""),
                        material=str(fields["material"].value or ""),
                        quantity_needed=str(fields["quantity_needed"].value or ""),
                        shortage=str(fields["issue_blocker"].value or ""),
                        needed_by_date=str(fields["needed_by_date"].value or ""),
                        notes_text=str(fields["notes"].value or ""),
                    )
                    output.value = f"{title}\n\n{body}"
                    ui.notify("Material shortage note created.", color="positive")

                ui.button("Generate Material Shortage Note", on_click=generate_shortage).props("unelevated color=primary")
            with ui.tab_panel(summary_tab):
                fields = {
                    "date": ui.input("Date", value=str(date.today().isoformat())),
                    "releases_worked": ui.textarea("Releases worked"),
                    "panels_completed": ui.input("Panels completed"),
                    "pallets_completed": ui.input("Pallets completed"),
                    "cnc_status": ui.input("CNC status"),
                    "assembly_status": ui.input("Assembly status"),
                    "shipping_status": ui.input("Shipping status"),
                    "blockers": ui.textarea("Blockers"),
                    "tomorrow_priorities": ui.textarea("Tomorrow priorities"),
                    "notes": ui.textarea("Notes"),
                }
                output = ui.textarea("Generated note").props("readonly").classes("w-full")

                def generate_summary() -> None:
                    summary_date = None
                    date_value = str(fields["date"].value or "").strip()
                    if date_value:
                        try:
                            summary_date = date.fromisoformat(date_value)
                        except ValueError:
                            summary_date = date.today()
                    title, body = notes.daily_production_summary(
                        summary_date=summary_date,
                        releases_worked=str(fields["releases_worked"].value or ""),
                        panels_completed=str(fields["panels_completed"].value or ""),
                        pallets_completed=str(fields["pallets_completed"].value or ""),
                        cnc_status=str(fields["cnc_status"].value or ""),
                        assembly_status=str(fields["assembly_status"].value or ""),
                        shipping_status=str(fields["shipping_status"].value or ""),
                        blockers=str(fields["blockers"].value or ""),
                        next_steps=str(fields["tomorrow_priorities"].value or ""),
                        notes_text=str(fields["notes"].value or ""),
                    )
                    output.value = f"{title}\n\n{body}"
                    ui.notify("Daily production summary created.", color="positive")

                ui.button("Generate Daily Production Summary", on_click=generate_summary).props("unelevated color=primary")
def _render_scripts_card() -> None:
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label("Scripts").classes("text-xl font-semibold")
        ui.label("Scripts run only from the Zorin host through the allowlisted launcher.")
        with ui.grid(columns=2).classes("w-full gap-3"):
            for key in [
                "mount_shares",
                "open_wireguard",
                "launch_autocad",
                "open_browser_tabs",
            ]:
                _action_card(key)


def _render_settings_card() -> None:
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label("Settings").classes("text-xl font-semibold")
        ui.label("Protected settings include host launch commands and mount commands.")
        with ui.row().classes("gap-3"):
            ui.button("Edit protected settings", on_click=_request_settings).props("unelevated color=primary").classes("min-h-[52px] px-5")
            ui.button("Refresh mount status", on_click=lambda: _run_action("refresh_job_index")).props("flat").classes("min-h-[52px] px-5")
        with ui.row().classes("gap-4 flex-wrap"):
            ui.label(f"Host: {_setting('app_host', DEFAULT_SETTINGS['app_host'])}")
            ui.label(f"Port: {_setting('app_port', DEFAULT_SETTINGS['app_port'])}")
            ui.label(f"Native: {'yes' if _setting('native_window', '0') == '1' else 'no'}")
            ui.label(f"Backup: {_setting('backup_dir', DEFAULT_SETTINGS['backup_dir'])}")


def _render_history_card() -> None:
    logs = db.list_action_logs(limit=10)
    searches = db.list_recent_searches(limit=10)
    backups = db.list_backups(limit=5)
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label("History / Logs").classes("text-xl font-semibold")
        with ui.tabs().classes("w-full") as tabs:
            actions_tab = ui.tab("Actions")
            searches_tab = ui.tab("Searches")
            backups_tab = ui.tab("Backups")
        with ui.tab_panels(tabs, value=actions_tab).classes("w-full bg-transparent"):
            with ui.tab_panel(actions_tab):
                for item in logs:
                    ui.separator()
                    ui.label(f'{item["created_at"]} | {item["action_key"]} | {"OK" if item["success"] else "FAIL"}')
                    ui.label(str(item["message"])).classes("text-xs text-slate-300")
            with ui.tab_panel(searches_tab):
                for item in searches:
                    ui.separator()
                    ui.label(f'{item["created_at"]} | {item["query"]} | {item["results_count"]} result(s)')
            with ui.tab_panel(backups_tab):
                for item in backups:
                    ui.separator()
                    ui.label(f'{item["created_at"]} | {item["status"]} | {item["backup_path"]}')


def _render_dashboard_top() -> None:
    with ui.card().classes("w-full bg-slate-900 text-slate-100"):
        ui.label(APP_NAME).classes("text-3xl font-bold")
        ui.label(f"Elward Systems Production Dashboard v{APP_VERSION}").classes("text-sm text-slate-300")
        with ui.row().classes("gap-2 flex-wrap mt-2"):
            ui.badge(f"Mode {_setting('network_mode', DEFAULT_SETTINGS['network_mode'])}", color="primary")
            ui.badge(f"Host {_setting('resolved_host', _setting('app_host', DEFAULT_SETTINGS['app_host']))}", color="primary")
            ui.badge(f"Port {_setting('resolved_port', _setting('app_port', DEFAULT_SETTINGS['app_port']))}", color="primary")
            ui.badge("Unlocked" if security.is_unlocked(app.storage.user) else "Locked", color="positive" if security.is_unlocked(app.storage.user) else "warning")
        ui.label("Current dashboard URL").classes("text-sm text-slate-300 mt-2")
        for url in _dashboard_urls():
            ui.label(url).classes("text-base font-semibold break-all")
        ui.separator()
        ui.label("Quick search").classes("text-sm text-slate-300")
        global SEARCH_INPUT
        SEARCH_INPUT = ui.input("Search jobs, releases, pallets, marks").props("clearable").classes("w-full")
        with ui.row().classes("gap-2 mt-2 flex-wrap"):
            ui.button("Search", on_click=_run_search).props("unelevated color=primary").classes("min-h-[52px] px-5")
            ui.button("Refresh Job Index", on_click=lambda: _run_action("refresh_job_index")).props("unelevated color=secondary").classes("min-h-[52px] px-5")
            ui.button("Backup Command Center DB", on_click=lambda: _run_action("backup_database")).props("unelevated color=secondary").classes("min-h-[52px] px-5")
        searches = db.list_recent_searches(limit=6)
        if searches:
            ui.label("Recent searches").classes("text-xs text-slate-400")
            with ui.row().classes("gap-2 flex-wrap"):
                for item in searches:
                    query = str(item["query"])
                    ui.button(f"{query} ({item['results_count']})", on_click=lambda q=query: _set_search_query(q)).props("flat")


def _render_quick_cards() -> None:
    with ui.element("div").classes("w-full grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"):
        _folder_status_card("Release Docs", "release_docs_path", SMB_PATHS["release_docs"])
        _folder_status_card("Drawings", "drawings_path", SMB_PATHS["drawings"])
        _folder_status_card("CNC Files", "cnc_files_path", SMB_PATHS["cnc_files"])
        _action_card("open_pallet_tracker")
        _action_card("open_all_releases")
        _action_card("launch_autocad")
        _action_card("mount_shares")
        _action_card("refresh_job_index")
        _action_card("backup_database")
        _action_card("create_blank_release_checklist")


@ui.page("/")
def dashboard() -> None:
    global PIN_DIALOG, SETTINGS_DIALOG
    ui.add_head_html(
        """
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0f172a" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="icon" href="/elward-icon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/elward-icon.svg" />
        <style>
          body { background: linear-gradient(180deg, #020617 0%, #0f172a 100%); color: #e2e8f0; }
          .nicegui-content { max-width: 1400px; margin: 0 auto; padding: 16px; }
        </style>
        """
    )
    PIN_DIALOG = _render_pin_dialog()
    SETTINGS_DIALOG = _render_settings_dialog()
    with ui.column().classes("w-full gap-4"):
        _render_dashboard_top()
        _render_pinned_job_card()
        _render_quick_cards()
        _render_search_card()
        _render_recent_jobs_card()
        _render_templates_card()
        _render_scripts_card()
        _render_settings_card()
        _render_history_card()


def register_routes() -> None:
    return None
