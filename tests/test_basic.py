import os
os.environ.setdefault("CIPHERHACKS_DB", os.path.join(os.path.dirname(__file__), "..", "test_tmp.db"))
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import create_app

def test_health():
    app = create_app()
    c = app.test_client()
    assert c.get("/healthz").get_json() == {"ok": True}

def test_signup_gating_quiz():
    app = create_app()
    c = app.test_client()
    c.post("/signup", data={"username": "tester1", "consent": "yes"})
    # recruit lesson reachable, operator locked
    assert c.get("/lesson/passwords-2fa").status_code == 200
    assert c.get("/lesson/linux-first-steps").status_code == 403
    # legal pages load, no third-party embeds
    for p in ["/privacy", "/terms", "/cookies", "/refunds", "/conduct", "/about"]:
        r = c.get(p)
        assert r.status_code == 200
        html = r.get_data(as_text=True).lower()
        assert "google-analytics" not in html and "googletag" not in html

def test_terminal_blocked():
    app = create_app()
    c = app.test_client()
    c.post("/signup", data={"username": "tester2", "consent": "yes"})
    r = c.post("/api/terminal", json={"lab_id": "linux-basics", "cmd": "ssh root@real"})
    assert r.status_code == 200
    assert "Blocked" in r.get_json()["output"]
    r2 = c.post("/api/terminal", json={"lab_id": "linux-basics", "cmd": "ls -la"})
    assert ".note" in r2.get_json()["output"]
