#!/bin/bash
# ROOT KIT PRO v2.0 - Quick Launcher
# Starts API + opens HTML in LibreWolf
set -euo pipefail

APP_DIR="$HOME/.rootkit-pro"

# Kill old API
pkill -f "api.py" 2>/dev/null || true
sleep 0.5

# Start API
python3 "$APP_DIR/backend/api.py" &
API_PID=$!
echo "$API_PID" > "$APP_DIR/api.pid"
sleep 1

# Open in LibreWolf
librewolf --no-remote "$APP_DIR/html/index.html" 2>/dev/null &
disown

echo "ROOT KIT PRO v2.0 running (API PID: $API_PID)"
echo "Close browser to auto-stop API"
