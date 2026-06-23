#!/bin/sh

# Credentials the server cannot boot without. settings.py resolves each via
# load_credential(), whose chain is credentials.json -> AWS Secrets Manager -> env
# var. credentials.json is gitignored and absent from CI-built images, so in
# production these come from the single Secrets Manager secret seeded by
# internal/sync_secret.sh (fetched via the ECS task role). If one is missing, Django
# still boots — load_credential() returns '' rather than raising — and only fails on
# a LATER request (e.g. the messages middleware dereferencing settings.SECRET_KEY),
# surfacing as recurring /health 500s with the real cause buried deep in a traceback.
# Resolve them the SAME way settings does (reusing load_credential so the two can't
# drift) and fail loudly at boot instead.
#
# Space-separated; add keys as the app grows new hard requirements, e.g.
#   REQUIRED_CREDENTIALS="SECRET_KEY DATABASE_PASSWORD JWT_SECRET"
# Keep roughly in sync with REQUIRED_SECRET_KEYS in scripts/deploy.py.
REQUIRED_CREDENTIALS="SECRET_KEY"

# Resolve every required credential in one Python call and collect the empties, so
# a single boot reports ALL missing keys at once instead of one-per-restart.
# $REQUIRED_CREDENTIALS is intentionally unquoted to word-split into argv.
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

# Start the ASGI server
exec daphne -b 0.0.0.0 -p 8000 grit.core.asgi:application
