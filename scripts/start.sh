#!/bin/sh
REQUIRED_CREDENTIALS="SECRET_KEY"
MISSING=$(python -c "
import sys
from grit.core.utils.env_config import load_credential
print(' '.join(k for k in sys.argv[1:] if not load_credential(k)))
" $REQUIRED_CREDENTIALS 2>/dev/null)
if [ -n "$MISSING" ]; then
  echo "Error: required credential(s) not set: $MISSING" >&2
  echo "Provide them via credentials.json (local), the AWS Secrets Manager secret" >&2
  echo "(production: seed it with internal/sync_secret.sh), or environment variables." >&2
  exit 1
fi
exec daphne -b 0.0.0.0 -p 8000 grit.core.asgi:application
