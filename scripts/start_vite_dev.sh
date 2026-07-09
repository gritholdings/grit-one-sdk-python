#!/bin/sh
set -e  # Exit on any error
echo "=== Starting Vite Dev Server with PID Management ==="
cd "$(dirname "$0")/../frontend"
PID_FILE="vite.pid"
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
trap cleanup EXIT SIGTERM SIGINT
if [ -f "$PID_FILE" ]; then
    echo "⚠️  Found stale PID file, removing..."
    rm -f "$PID_FILE"
fi
echo "Starting Vite dev server..."
echo "PID file will be created at: $(pwd)/$PID_FILE"
npm run dev &
VITE_PID=$!
echo $VITE_PID > "$PID_FILE"
echo "✓ Vite dev server started with PID: $VITE_PID"
echo "✓ PID file created: $PID_FILE"
wait $VITE_PID
VITE_EXIT_CODE=$?
if [ $VITE_EXIT_CODE -ne 0 ]; then
    echo "❌ Vite process crashed with exit code: $VITE_EXIT_CODE"
    exit $VITE_EXIT_CODE
fi
echo "Vite dev server stopped normally"
exit 0
