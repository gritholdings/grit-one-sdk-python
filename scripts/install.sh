#!/bin/sh
set -e  # Exit on any error
cd frontend
npx @tailwindcss/cli -i ./input.css -o ../home/static/home/global.css

# Check if we're in development mode
if [ "$DEVELOPMENT_MODE" = "true" ] || [ "$DJANGO_ENV" = "DEV" ]; then
    echo "Starting Vite dev server for hot reload..."
    # Start Vite dev server in the background
    npm run dev &
    VITE_PID=$!
    echo "Vite dev server started with PID: $VITE_PID"
    # Save PID to a file for potential cleanup later
    echo $VITE_PID > vite.pid
else
    echo "Building frontend for production..."
    npm run build
fi

cd ..