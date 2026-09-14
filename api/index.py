import os
import sys

# Vercel runs this file as api/index.py. Ensure project root is importable.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# The Flask app (path normalization already applied inside create_app,
# so this entrypoint works no matter how Vercel invokes it).
from app import _StripApiPrefix  # noqa: E402,F401  (shared, single source)
from app import app  # noqa: E402  -- Vercel looks for `app` variable
