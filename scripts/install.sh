#!/bin/sh
set -e  # Exit on any error
echo "=== Install Script Starting ==="
echo "DJANGO_ENV: $DJANGO_ENV"
echo "DEVELOPMENT_MODE: $DEVELOPMENT_MODE"
PYTHON="${PYTHON_PATH:-./env/bin/python}"
echo "Using Python: $PYTHON"
cd frontend
npm run build:css
if [ "$DEVELOPMENT_MODE" = "true" ]; then
    echo "Development mode: Preparing environment for Vite dev server..."
    echo "Note: Vite dev server will be started by VS Code task orchestration"
    if [ -f "vite.pid" ]; then
        OLD_PID=$(cat vite.pid)
        if ps -p $OLD_PID > /dev/null 2>&1; then
            echo "Killing old Vite process (PID: $OLD_PID)..."
            kill $OLD_PID 2>/dev/null || true
            sleep 1
        fi
        rm -f vite.pid
        echo "Removed stale vite.pid file"
    fi
    EXISTING_PIDS=$(lsof -ti:5173 2>/dev/null || true)
    if [ ! -z "$EXISTING_PIDS" ]; then
        echo "Killing existing process(es) on port 5173: $EXISTING_PIDS"
        for PID in $EXISTING_PIDS; do
            kill $PID 2>/dev/null || true
        done
        sleep 1
    fi
    echo "Environment prepared. Vite will be started by the next task in sequence."
fi
if [ "$DJANGO_ENV" = "PROD" ]; then
    echo "Building frontend for production..."
    if [ -f "vite.pid" ]; then
        echo "Removing old vite.pid file..."
        rm vite.pid
    fi
    npm run build
    cd ..
    echo "Collecting static files for production..."
    DJANGO_ENV=PROD $PYTHON manage.py collectstatic --noinput
else
    cd ..
fi