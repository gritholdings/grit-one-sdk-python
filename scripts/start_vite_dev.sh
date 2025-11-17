#!/bin/sh
set -e  # Exit on any error

echo "=== Starting Vite Dev Server with PID Management ==="

# Change to frontend directory
cd "$(dirname "$0")/../frontend"

PID_FILE="vite.pid"

# Cleanup function to remove PID file on exit
cleanup() {
    EXIT_CODE=$?
    echo ""
    echo "=== Vite Dev Server Stopping ==="
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "Cleaning up PID file (Process: $PID)..."
        rm -f "$PID_FILE"
        echo "PID file removed"
    fi
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️  Vite exited with code $EXIT_CODE (may indicate a crash)"
    fi
    exit $EXIT_CODE
}

# Register cleanup trap for all exit scenarios
# SIGTERM: VS Code task termination, kill command
# SIGINT: Ctrl+C
# EXIT: Any script exit (including errors)
trap cleanup EXIT SIGTERM SIGINT

# Remove stale PID file if it exists
if [ -f "$PID_FILE" ]; then
    echo "⚠️  Found stale PID file, removing..."
    rm -f "$PID_FILE"
fi

echo "Starting Vite dev server..."
echo "PID file will be created at: $(pwd)/$PID_FILE"

# Start Vite in background and capture its PID
npm run dev &
VITE_PID=$!

# Write PID to file
echo $VITE_PID > "$PID_FILE"
echo "✓ Vite dev server started with PID: $VITE_PID"
echo "✓ PID file created: $PID_FILE"

# Wait for Vite process and monitor its health
# This blocks until Vite exits (either gracefully or via crash)
wait $VITE_PID
VITE_EXIT_CODE=$?

# If Vite crashed (non-zero exit), report it
if [ $VITE_EXIT_CODE -ne 0 ]; then
    echo "❌ Vite process crashed with exit code: $VITE_EXIT_CODE"
    exit $VITE_EXIT_CODE
fi

echo "Vite dev server stopped normally"
exit 0
