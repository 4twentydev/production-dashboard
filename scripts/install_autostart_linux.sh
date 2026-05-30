#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
AUTOSTART_SRC="$ROOT_DIR/desktop/elward-command-center-autostart.desktop"
AUTOSTART_DST="$AUTOSTART_DIR/elward-command-center.desktop"

mkdir -p "$AUTOSTART_DIR"
sed "s|__ELWARD_WCC_ROOT__|$ROOT_DIR|g" "$AUTOSTART_SRC" > "$AUTOSTART_DST"
chmod 644 "$AUTOSTART_DST"

echo "Installed autostart entry: $AUTOSTART_DST"
echo "The dashboard will start after login."

