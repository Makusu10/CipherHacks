import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CIPHERHACKS_DB", os.path.join(BASE_DIR, "cipherhacks.db"))
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "change-me-dev-only")
