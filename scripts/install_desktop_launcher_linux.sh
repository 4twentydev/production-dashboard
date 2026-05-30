#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
LAUNCHER_SRC="$ROOT_DIR/desktop/elward-command-center.desktop"
LAUNCHER_DST="$APP_DIR/elward-command-center.desktop"

mkdir -p "$APP_DIR"
sed "s|__ELWARD_WCC_ROOT__|$ROOT_DIR|g" "$LAUNCHER_SRC" > "$LAUNCHER_DST"
chmod 644 "$LAUNCHER_DST"

echo "Installed launcher: $LAUNCHER_DST"
echo "Open your app menu and search for Elward Command Center."

