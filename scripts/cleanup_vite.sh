#!/bin/sh

echo "=== Vite Cleanup Script ==="

# Check if vite.pid file exists and kill the process
if [ -f "frontend/vite.pid" ]; then
    PID=$(cat frontend/vite.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Killing Vite process from pid file (PID: $PID)..."
        kill $PID 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null || true
        fi
    else
        echo "Process $PID not found (already stopped)"
    fi
    rm frontend/vite.pid
    echo "Removed vite.pid file"
fi

# Check for any processes on port 5173
echo "Checking for processes on port 5173..."
VITE_PIDS=$(lsof -ti:5173 2>/dev/null || true)
if [ ! -z "$VITE_PIDS" ]; then
    echo "Found process(es) on port 5173: $VITE_PIDS"
    for PID in $VITE_PIDS; do
        echo "Killing process $PID..."
        kill $PID 2>/dev/null || true
    done
    sleep 1
    # Force kill any remaining
    for PID in $VITE_PIDS; do
        if ps -p $PID > /dev/null 2>&1; then
            echo "Force killing process $PID..."
            kill -9 $PID 2>/dev/null || true
        fi
    done
    echo "All processes on port 5173 have been terminated"
else
    echo "No processes found on port 5173"
fi

# Also check for any node processes running vite
echo "Checking for Vite node processes..."
VITE_NODE_PIDS=$(ps aux | grep -E "node.*vite" | grep -v grep | awk '{print $2}' || true)
if [ ! -z "$VITE_NODE_PIDS" ]; then
    echo "Found Vite node process(es): $VITE_NODE_PIDS"
    for PID in $VITE_NODE_PIDS; do
        echo "Killing Vite node process $PID..."
        kill $PID 2>/dev/null || true
    done
fi

echo "=== Vite Cleanup Complete ==="
