#!/bin/sh
set -e  # Exit on any error
cd frontend
npx @tailwindcss/cli -i ./input.css -o ../home/static/home/global.css
npm run build
cd ..