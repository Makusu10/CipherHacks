import os
import sys

# Vercel runs this file as api/index.py. Ensure project root is importable.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app  # noqa: E402  -- Vercel looks for `app` variable


class _StripApiPrefix:
    """Vercel invokes this file at /api/index, and some rewrite setups hand
    Flask the destination path (/api/index...) instead of the original URL.
    Flask then 404s every page, including `/`. Normalize it back; requests
    that already carry the right path pass through untouched."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or "/"
        for prefix in ("/api/index.py", "/api/index"):
            if path == prefix:
                path = "/"
                break
            if path.startswith(prefix + "/"):
                path = path[len(prefix):] or "/"
                break
        environ["PATH_INFO"] = path
        return self.wsgi_app(environ, start_response)


app.wsgi_app = _StripApiPrefix(app.wsgi_app)
