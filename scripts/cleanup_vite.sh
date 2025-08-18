#!/bin/sh
# Script to cleanup Vite dev server process

if [ -f "frontend/vite.pid" ]; then
    PID=$(cat frontend/vite.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping Vite dev server (PID: $PID)..."
        kill $PID
        rm frontend/vite.pid
        echo "Vite dev server stopped."
    else
        echo "Vite dev server process not found, cleaning up PID file..."
        rm frontend/vite.pid
    fi
else
    echo "No Vite dev server PID file found."
fi