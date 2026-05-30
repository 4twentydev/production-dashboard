# Elward Work Command Center

Local Python/NiceGUI dashboard for Elward production work.

## What this is

- A local-first daily tool for Elward production work only.
- Main host: Zorin/Linux.
- Secondary desktop access: Windows.
- Mobile access: Android and iOS as a PWA-style dashboard.
- The Zorin host performs folder, file, and script actions.
- Mobile clients can search jobs, open Monday links, view results, trigger allowed host actions, and generate notes/templates.

## Project layout

- `app.py` main launcher
- `database.py` SQLite helpers
- `models.py` shared dataclasses
- `launcher.py` safe host-launch boundary
- `job_indexer.py` indexing and search
- `templates.py` note/template builders
- `scripts.py` action allowlist
- `security.py` PIN handling
- `seed.py` database/bootstrap seeding
- `config.py` defaults and paths
- `desktop/` launcher templates and icon
- `scripts/` helper scripts
- `src/elward_wcc/` implementation package

## Install

```bash
python3 -m pip install -r requirements.txt
```

If you are using a virtual environment, activate it first.

## Run

```bash
python3 app.py
```

NiceGUI native mode or browser mode is controlled from Settings:

- `native_window = 1` uses NiceGUI native mode on the host.
- `native_window = 0` runs as a browser-hosted dashboard.

## Zorin setup

### Install CIFS support

```bash
sudo apt update
sudo apt install cifs-utils
```

### Create mount points

```bash
sudo mkdir -p /mnt/elward/release-docs /mnt/elward/drawings /mnt/elward/cnc-files
```

### Manual mount test examples

Guest mount examples:

```bash
sudo mount -t cifs //192.168.2.6/release\ docs /mnt/elward/release-docs -o guest,uid=1000,gid=1000,iocharset=utf8
sudo mount -t cifs //192.168.2.6/drawings /mnt/elward/drawings -o guest,uid=1000,gid=1000,iocharset=utf8
sudo mount -t cifs //192.168.2.6/cnc\ files /mnt/elward/cnc-files -o guest,uid=1000,gid=1000,iocharset=utf8
```

Credentials-file example:

```bash
sudo install -m 600 /dev/null /etc/samba/elward.credentials
sudo nano /etc/samba/elward.credentials
```

Example file contents:

```ini
username=YOUR_USERNAME
password=YOUR_PASSWORD
domain=YOUR_DOMAIN
```

Example mount command:

```bash
sudo mount -t cifs //192.168.2.6/release\ docs /mnt/elward/release-docs -o credentials=/etc/samba/elward.credentials,uid=1000,gid=1000,iocharset=utf8
```

Do not store SMB credentials in the app.

## Desktop launcher

Install a user-level launcher for Zorin/Linux:

```bash
bash scripts/install_desktop_launcher_linux.sh
```

This creates a launcher in:

- `~/.local/share/applications/elward-command-center.desktop`

The launcher starts the app using the current repo path and honors the `native_window` setting.

## Autostart

Install autostart for login:

```bash
bash scripts/install_autostart_linux.sh
```

Disable autostart:

```bash
bash scripts/remove_autostart_linux.sh
```

Autostart is user-level only and does not require `sudo`.

## LAN access

The dashboard shows the current URL in the UI after startup.

Default behavior:

- `network_mode = lan` binds to the LAN and serves on the current host IP.
- `network_mode = local` binds to `127.0.0.1` only.
- `network_mode = custom` uses the configured host value.

Default port is `8080`. If it is already in use, the app automatically moves to the next free port and shows the resolved URL.

Windows, Android, and iOS can open the dashboard over the same network using the displayed URL.

## Mobile install

Android:

1. Open the dashboard URL in Chrome.
2. Use the browser menu to add/install it to the home screen.

iOS:

1. Open the dashboard URL in Safari.
2. Use Share to add it to the Home Screen.

The app includes a manifest and icon placeholder to improve install behavior.

## Windows access

- Open the dashboard URL in a browser on the Windows machine.
- Folder actions resolve to the Zorin host paths, not local Windows SMB mounts.
- If you run the app on Windows as a host, folder opening uses Windows-style shell behavior where practical.
- Do not make Windows the main target unless you explicitly reconfigure the host and paths.

## Security

- Settings and scripts require a PIN.
- Destructive shell commands are blocked.
- SMB credentials are not stored.
- Actions are allowlisted.
- Action logs do not store secrets.

## Backups

- Use the `Backup Command Center DB` button in the app.
- The backup folder is configurable in Settings.
- Backups use timestamped filenames.

## Troubleshooting

- If a folder path is missing, the app shows the nearest existing parent folder and a warning.
- If a mount is missing, use the Mount Elward Shares action after verifying your host-side mount configuration.
- If the port is busy, the app will choose the next available port and show the resolved dashboard URL.
- If the dashboard does not open in native mode, set `native_window = 1` in Settings or run it from the desktop launcher after installing it.

## Elward paths

Local mount points:

- `/mnt/elward/release-docs`
- `/mnt/elward/drawings`
- `/mnt/elward/cnc-files`

Original SMB references:

- `smb://192.168.2.6/release%20docs`
- `smb://192.168.2.6/drawings`
- `smb://192.168.2.6/cnc%20files`

Monday links:

- Pallet Tracker: `https://elward.monday.com/boards/18401421784`
- All Releases: `https://elward.monday.com/boards/18396225616/views/246248170`
