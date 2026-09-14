import os
import sys

# Vercel runs this file as api/index.py. Ensure project root is importable.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app  # noqa: E402  -- Vercel looks for `app` variable


class _StripApiPrefix:
    """Vercel serves this file at /api/index and splits that destination
    across SCRIPT_NAME + PATH_INFO (e.g. SCRIPT_NAME=/api, PATH_INFO=/index
    for a request to `/`). Flask matches on PATH_INFO alone, so every page
    404s unless the function-name head is removed. Requests that already
    carry the right path pass through untouched."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        script = environ.get("SCRIPT_NAME") or ""
        path = environ.get("PATH_INFO") or "/"
        if (script == "/api" or script.startswith("/api/")) and (
            path == "/index" or path.startswith("/index/")
        ):
            path = path[len("/index"):] or "/"
            environ["SCRIPT_NAME"] = ""
        for prefix in ("/api/index.py", "/api/index"):
            if path == prefix:
                path = "/"
                break
            if path.startswith(prefix + "/"):
                path = path[len(prefix):] or "/"
                break
        environ["PATH_INFO"] = path or "/"
        return self.wsgi_app(environ, start_response)


app.wsgi_app = _StripApiPrefix(app.wsgi_app)
