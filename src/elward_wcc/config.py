from __future__ import annotations

import json
from pathlib import Path

APP_NAME = "Elward Work Command Center"
APP_VERSION = "0.1.0"

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "elward_wcc.sqlite3"

MOUNT_PATHS = {
    "release_docs": Path("/mnt/elward/release-docs"),
    "drawings": Path("/mnt/elward/drawings"),
    "cnc_files": Path("/mnt/elward/cnc-files"),
}

SMB_PATHS = {
    "release_docs": "smb://192.168.2.6/release%20docs",
    "drawings": "smb://192.168.2.6/drawings",
    "cnc_files": "smb://192.168.2.6/cnc%20files",
}

ELWARD_URLS = {
    "pallet_tracker": "https://elward.monday.com/boards/18401421784",
    "all_releases": "https://elward.monday.com/boards/18396225616/views/246248170",
}

DEFAULT_BROWSER_TABS = [
    ELWARD_URLS["pallet_tracker"],
    ELWARD_URLS["all_releases"],
]

DEFAULT_MOUNT_COMMANDS = [
    [
        "sudo",
        "-n",
        "mount",
        "-t",
        "cifs",
        "//192.168.2.6/release docs",
        "/mnt/elward/release-docs",
        "-o",
        "guest,uid=1000,gid=1000,iocharset=utf8",
    ],
    [
        "sudo",
        "-n",
        "mount",
        "-t",
        "cifs",
        "//192.168.2.6/drawings",
        "/mnt/elward/drawings",
        "-o",
        "guest,uid=1000,gid=1000,iocharset=utf8",
    ],
    [
        "sudo",
        "-n",
        "mount",
        "-t",
        "cifs",
        "//192.168.2.6/cnc files",
        "/mnt/elward/cnc-files",
        "-o",
        "guest,uid=1000,gid=1000,iocharset=utf8",
    ],
]

DEFAULT_SETTINGS = {
    "app_host": "0.0.0.0",
    "app_port": "8080",
    "network_mode": "lan",
    "native_window": "0",
    "pin_unlock_minutes": "480",
    "pin_lockout_minutes": "10",
    "pinned_job_id": "",
    "pinned_job_label": "",
    "backup_dir": str(BACKUP_DIR),
    "release_docs_path": str(MOUNT_PATHS["release_docs"]),
    "drawings_path": str(MOUNT_PATHS["drawings"]),
    "cnc_files_path": str(MOUNT_PATHS["cnc_files"]),
    "release_docs_smb_path": SMB_PATHS["release_docs"],
    "drawings_smb_path": SMB_PATHS["drawings"],
    "cnc_files_smb_path": SMB_PATHS["cnc_files"],
    "pallet_tracker_url": ELWARD_URLS["pallet_tracker"],
    "all_releases_url": ELWARD_URLS["all_releases"],
    "browser_tab_urls": json.dumps(DEFAULT_BROWSER_TABS),
    "autocad_command": "[]",
    "wireguard_command": "[]",
    "mount_commands_json": json.dumps(DEFAULT_MOUNT_COMMANDS),
}
