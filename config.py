import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Vercel serverless filesystem is read-only except /tmp.
# SQLite must live in /tmp on Vercel, otherwise every request
# crashes with FUNCTION_INVOCATION_FAILED.
_DEFAULT_DB = os.path.join(BASE_DIR, "cipherhacks.db")
if os.environ.get("VERCEL") == "1" and "CIPHERHACKS_DB" not in os.environ:
    _DEFAULT_DB = os.path.join("/tmp", "cipherhacks.db")

DB_PATH = os.environ.get("CIPHERHACKS_DB", _DEFAULT_DB)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "change-me-dev-only")
