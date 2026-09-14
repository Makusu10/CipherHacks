import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CIPHERHACKS_DB",
                      os.path.join(os.path.dirname(__file__), "..", "test_tmp.db"))

_API = os.path.join(os.path.dirname(__file__), "..", "api", "index.py")
_mod = None


def _handler_client():
    global _mod
    if _mod is None:
        spec = importlib.util.spec_from_file_location("vercel_index", _API)
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)
    return _mod.app.test_client()


def test_vercel_destination_path_serves_home():
    # Vercel rewrites /(.*) -> /api/index; if Flask sees the destination
    # path instead of the original URL, every page 404s (the reported bug).
    c = _handler_client()
    r = c.get("/", environ_overrides={"PATH_INFO": "/api/index"})
    html = r.get_data(as_text=True)
    assert r.status_code == 200, html[:200]
    assert "Type your" in html
    assert "No such page" not in html


def test_vercel_nested_and_static_paths():
    c = _handler_client()
    r = c.get("/labs", environ_overrides={"PATH_INFO": "/api/index/labs"})
    assert r.status_code == 200
    assert "Practice boxes" in r.get_data(as_text=True)
    r = c.get("/static/css/style.css",
              environ_overrides={"PATH_INFO": "/api/index/static/css/style.css"})
    assert r.status_code == 200


def test_normal_paths_untouched():
    c = _handler_client()
    assert c.get("/").status_code == 200
    assert c.get("/nope-not-real").status_code == 404
