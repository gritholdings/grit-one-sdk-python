#!/bin/sh
set -e  # Exit on any error
cd frontend
npx tailwindcss -i ./input.css -o ../home/static/home/global.css --config tailwind.config.js
cd ..