import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CIPHERHACKS_DB",
                      os.path.join(os.path.dirname(__file__), "..", "test_tmp.db"))

from app import _StripApiPrefix, create_app  # noqa: E402


def _client():
    return create_app().test_client()


def test_framework_true_paths():
    # Vercel's framework preset routes every request to root app.py with the
    # real path (no rewrites). This is the primary serving mode.
    c = _client()
    assert c.get("/").status_code == 200
    assert "Type your" in c.get("/").get_data(as_text=True)
    assert c.get("/labs").status_code == 200
    assert c.get("/static/css/style.css").status_code == 200
    assert c.get("/nope-not-real").status_code == 404


def test_destination_path_shapes():
    # If a rewrite ever resurfaces a destination path (/api/index...) instead
    # of the original URL, the middleware must still resolve correctly.
    c = _client()
    r = c.get("/", environ_overrides={"PATH_INFO": "/api/index"})
    assert r.status_code == 200
    assert "Type your" in r.get_data(as_text=True)
    assert "No such page" not in r.get_data(as_text=True)


def test_vercel_nested_and_static_paths():
    c = _client()
    r = c.get("/labs", environ_overrides={"PATH_INFO": "/api/index/labs"})
    assert r.status_code == 200
    assert "Practice boxes" in r.get_data(as_text=True)
    r = c.get("/static/css/style.css",
              environ_overrides={"PATH_INFO": "/api/index/static/css/style.css"})
    assert r.status_code == 200


def test_vercel_path_shapes():
    c = _client()
    for shape in ["/api/index", "/api/index/", "/api/index.py",
                  "/api/index.py/"]:
        r = c.get("/", environ_overrides={"PATH_INFO": shape})
        assert r.status_code == 200, shape
        assert "Type your" in r.get_data(as_text=True), shape


def test_vercel_script_name_split():
    # Live forensics (view-source): Vercel sent SCRIPT_NAME=/api with the
    # function name as head of PATH_INFO. This exact shape 404d everything.
    c = _client()
    r = c.get("/", environ_overrides={"SCRIPT_NAME": "/api",
                                      "PATH_INFO": "/index"})
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Type your" in html
    r = c.get("/__route_debug",
              environ_overrides={"SCRIPT_NAME": "/api",
                                 "PATH_INFO": "/index/__route_debug"})
    assert r.status_code == 200
    assert r.get_json()["flask_path"] == "/__route_debug"
    r = c.get("/static/css/style.css",
              environ_overrides={"SCRIPT_NAME": "/api",
                                 "PATH_INFO": "/index/static/css/style.css"})
    assert r.status_code == 200


def test_normal_paths_untouched():
    c = _client()
    assert c.get("/").status_code == 200
    assert c.get("/nope-not-real").status_code == 404


def test_factory_applies_strip_regardless_of_entrypoint():
    # The serving entrypoint on Vercel may be root app.py, not api/index.py,
    # so normalization must live in create_app itself.
    w = create_app().wsgi_app
    assert isinstance(w, _StripApiPrefix)


def test_error_pages_never_cached():
    c = _client()
    r = c.get("/nope-not-real")
    assert r.status_code == 404
    assert "no-store" in r.headers.get("Cache-Control", "")
