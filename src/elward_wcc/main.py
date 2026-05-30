from __future__ import annotations

import os
import socket

from nicegui import ui

from . import actions, db
from .config import APP_NAME
from .web import register_routes


def _bind_host() -> str:
    mode = db.get_setting("network_mode", "lan") or "lan"
    if mode == "local":
        return "127.0.0.1"
    if mode == "custom":
        host = (db.get_setting("app_host", "0.0.0.0") or "0.0.0.0").strip()
        return host or "0.0.0.0"
    return "0.0.0.0"


def _port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _find_available_port(host: str, preferred: int) -> int:
    port = max(preferred, 1)
    for _ in range(50):
        if _port_is_available(host, port):
            return port
        port += 1
    return preferred


def _local_ip_address() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main() -> None:
    db.init_db()
    actions.ensure_registry()
    register_routes()

    host = _bind_host()
    port_raw = db.get_setting("app_port", "8080") or "8080"
    try:
        preferred_port = int(port_raw)
    except ValueError:
        preferred_port = 8080
    port = _find_available_port(host, preferred_port)
    db.set_setting("resolved_host", host, protected=False)
    db.set_setting("resolved_port", str(port), protected=False)
    dashboard_host = _local_ip_address() if host == "0.0.0.0" else host
    db.set_setting("dashboard_url", f"http://{dashboard_host}:{port}", protected=False)
    db.set_setting("dashboard_url_local", f"http://127.0.0.1:{port}", protected=False)
    native = (db.get_setting("native_window", "0") == "1") or os.environ.get("ELWARD_NATIVE", "0") == "1"
    try:
        ui.run(
            title=APP_NAME,
            host=host,
            port=port,
            reload=False,
            show=not native,
            native=native,
        )
    except Exception:
        ui.run(
            title=APP_NAME,
            host=host,
            port=port,
            reload=False,
            show=True,
        )


if __name__ == "__main__":
    main()
