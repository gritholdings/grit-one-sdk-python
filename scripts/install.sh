#!/bin/sh
set -e  # Exit on any error

echo "=== Install Script Starting ==="
echo "DJANGO_ENV: $DJANGO_ENV"
echo "DEVELOPMENT_MODE: $DEVELOPMENT_MODE"

# Use PYTHON_PATH from environment if set, otherwise use default
PYTHON="${PYTHON_PATH:-./env/bin/python}"
echo "Using Python: $PYTHON"

cd frontend
npx @tailwindcss/cli -i ./input.css -o ../home/static/home/global.css

# Check if we're in development mode
if [ "$DEVELOPMENT_MODE" = "true" ] || [ "$DJANGO_ENV" = "DEV" ]; then
    echo "Starting Vite dev server for hot reload..."
    # Remove any stale pid file first
    rm -f vite.pid
    # Start Vite dev server in the background
    npm run dev &
    VITE_PID=$!
    echo "Vite dev server started with PID: $VITE_PID"
    # Save PID to a file for potential cleanup later
    echo $VITE_PID > vite.pid
fi

if [ "$DJANGO_ENV" = "PROD" ]; then
    echo "Building frontend for production..."
    # Clean up any existing vite.pid file from previous dev runs
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