#!/bin/sh

# Check if the credentials.json file exists
if [ ! -f "credentials.json" ]; then
  echo "Error: credentials.json file not found."
  exit 1
fi

# Extract the OPENAI_API_KEY from credentials.json using Python
export OPENAI_API_KEY=$(python -c "
import json, sys
try:
    with open('credentials.json') as f:
        creds = json.load(f)
        print(creds.get('OPENAI_API_KEY', ''))
except Exception as e:
    print(f'Error: {str(e)}', file=sys.stderr)
    sys.exit(1)
")

# Check if the OPENAI_API_KEY was set successfully
if [ -z "$OPENAI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY could not be set or is empty."
  exit 1
else
  echo "OPENAI_API_KEY is set successfully."
fi

# Start the Gunicorn server
exec gunicorn --bind 0.0.0.0:8000 chatbot.wsgi:application