#!/bin/sh

# Install Tailwind CSS
cd frontend
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
chmod +x tailwindcss-macos-arm64

./tailwindcss-macos-arm64 -i ./global.css -o ../home/static/home/global.css --minify

rm tailwindcss-macos-arm64
cd ..