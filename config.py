import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Vercel serverless filesystem is read-only except /tmp.
# SQLite must live in /tmp on Vercel, otherwise every request
# crashes with FUNCTION_INVOCATION_FAILED.
# NOTE: /tmp is per-instance and ephemeral — accounts vanish on cold
# start and differ between concurrent instances. That is exactly the
# "auto logged out + can't log back in" bug. For true persistence on
# Vercel, set DATABASE_URL (Vercel Postgres / Neon) — see utils/db.py.
# Without it, the app self-heals sessions (stays logged in, handle
# re-created) but XP/progress still resets on cold start (demo mode).
_DEFAULT_DB = os.path.join(BASE_DIR, "cipherhacks.db")
if os.environ.get("VERCEL") == "1" and "CIPHERHACKS_DB" not in os.environ:
    _DEFAULT_DB = os.path.join("/tmp", "cipherhacks.db")

DB_PATH = os.environ.get("CIPHERHACKS_DB", _DEFAULT_DB)

# Persistent backend when available. Vercel Postgres exposes
# POSTGRES_URL (pooled) / POSTGRES_PRISMA_URL / POSTGRES_URL_NON_POOLING;
# a generic DATABASE_URL also works (Neon, Supabase, etc.).
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_PRISMA_URL")
    or os.environ.get("POSTGRES_URL_NON_POOLING")
    or ""
).strip()

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "change-me-dev-only")

# Sessions: 30-day signed cookie so browser restarts don't log users out.
# The cookie itself survives Vercel multi-instance (it is client-side);
# only the SQLite row didn't — fixed via self-healing in app.current_user.
PERMANENT_SESSION_LIFETIME = timedelta(days=30)

# Behind Vercel's HTTPS, mark the cookie Secure; locally keep False so
# plain-http http://127.0.0.1:5000 still sends it.
SESSION_COOKIE_SECURE = os.environ.get(
    "SESSION_COOKIE_SECURE",
    "1" if os.environ.get("VERCEL") == "1" else "0",
) == "1"
