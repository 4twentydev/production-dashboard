#!/usr/bin/env bash
set -euo pipefail

AUTOSTART_DST="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/elward-command-center.desktop"

if [ -f "$AUTOSTART_DST" ]; then
  rm -f "$AUTOSTART_DST"
  echo "Removed autostart entry: $AUTOSTART_DST"
else
  echo "No autostart entry found at: $AUTOSTART_DST"
fi

