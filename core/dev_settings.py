# Local development settings

# # Debug settings
# DEBUG = True

# # CSRF settings for local development
CSRF_COOKIE_SECURE = False  # Allow cookies over HTTP for local development
CSRF_COOKIE_DOMAIN = None  # Use localhost domain
# CSRF_COOKIE_SAMESITE = 'Lax'  # Keep the default SameSite policy

# # Override ALLOWED_HOSTS for local development
# ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# # Override CORS settings for local development
# CORS_ALLOWED_ORIGINS = [
#     'http://127.0.0.1:8000',
#     'http://localhost:8000',
# ]

# CSRF_TRUSTED_ORIGINS = [
#     'http://127.0.0.1:8000',
#     'http://localhost:8000',
# ]

# # Add any additional local-specific settings below