import os
import uuid
os.environ.setdefault("CIPHERHACKS_DB", os.path.join(os.path.dirname(__file__), "..", "test_tmp.db"))
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import create_app

def _handle(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def test_health():
    app = create_app()
    c = app.test_client()
    assert c.get("/healthz").get_json() == {"ok": True}

def test_signup_gating_quiz():
    app = create_app()
    c = app.test_client()
    c.post("/signup", data={"username": _handle("tester1"), "consent": "yes"})
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
    # guest terminal works, abuse blocked
    r = c.post("/api/terminal", json={"lab_id": "linux-basics", "cmd": "ssh root@real"})
    assert r.status_code == 200
    assert "Blocked" in r.get_json()["output"]
    r2 = c.post("/api/terminal", json={"lab_id": "linux-basics", "cmd": "ls -la"})
    assert ".note" in r2.get_json()["output"]

def test_free_modes():
    app = create_app()
    c = app.test_client()
    # guest-first: no signup needed to try
    assert c.get("/flashcards").status_code == 200
    assert c.get("/exams").status_code == 200
    assert c.get("/labs").status_code == 200
    assert c.get("/lab/linux-basics").status_code == 200
    assert c.get("/lesson/passwords-2fa").status_code == 200
    # guest quiz POST shows score, banks nothing
    r = c.post("/lesson/passwords-2fa", data={"q0": "0", "q1": "1", "q2": "0"})
    assert r.status_code == 200
    assert "Guest try" in r.get_data(as_text=True)
    # ranked modes still need a handle
    assert c.get("/arena").status_code == 302
    assert c.get("/guilds").status_code == 302
    home = c.get("/").get_data(as_text=True)
    assert "no signup" in home.lower()

def test_full_ladder():
    import json as _json
    app = create_app()
    c = app.test_client()
    # all six bands present with checkpoints
    data = open("data/curriculum.json", encoding="utf-8").read()
    lessons = _json.loads(data)
    bands = {l["band"] for l in lessons}
    assert {"recruit", "operator", "analyst", "specialist", "redteam", "apex"} <= bands
    for cp in ["recruit-checkpoint", "operator-checkpoint", "analyst-checkpoint",
               "specialist-checkpoint", "redteam-checkpoint", "apex-checkpoint"]:
        assert any(l["slug"] == cp for l in lessons), cp
    # recruit has no terminal talk; operator+ does
    rec = [l for l in lessons if l["band"] == "recruit"]
    assert all("terminal" not in (l["slug"]) for l in rec)
    # new labs answer without login
    for lab, cmd, expect in [
        ("privesc-sim", "sudo -l", "run_backup"),
        ("bof-sim", "check offset 64", "offset 64"),
        ("ssrf-sim", "fetch --internal", "flag{server_fetched_wrong_url}"),
        ("cloud-sim", "list-buckets", "invoices-2026"),
        ("logs-sim", "grep FAIL auth.log", "02:14"),
    ]:
        r = c.post("/api/terminal", json={"lab_id": lab, "cmd": cmd})
        assert r.status_code == 200, lab
        assert expect in r.get_json()["output"], lab
    # band-priced hints: red lab tier-0 costs more than recruit base
    c.post("/signup", data={"username": _handle("pricetester"), "consent": "yes"})
    h1 = c.post("/api/hint", json={"lab_id": "linux-basics", "tier": 0}).get_json()
    h2 = c.post("/api/hint", json={"lab_id": "ssrf-sim", "tier": 0}).get_json()
    assert h1["cost"] == 5 and h2["cost"] > h1["cost"]

def test_game_layer():
    from utils.leveling import rank_title, BAND_DOSSIER
    assert rank_title(1) == "Street Awake"
    assert rank_title(100) == "Apex Myth"
    assert set(BAND_DOSSIER) == {"recruit", "operator", "analyst", "specialist", "redteam", "apex"}
    app = create_app()
    c = app.test_client()
    assert c.get("/missions").status_code == 200
    assert "Case 01" in c.get("/missions").get_data(as_text=True)
    lb = c.get("/leaderboards").get_data(as_text=True)
    assert "Flag hunters" in lb and "Duelists" in lb

def test_grader_mediums():
    import re
    app = create_app()
    c = app.test_client()
    home = c.get("/").get_data(as_text=True)
    words = len(re.sub(r"<[^>]+>", " ", home).split())
    assert words >= 800, words
    assert "Frequently asked questions" in home
    assert home.count("<h3>") >= 6
    assert '"@type": "FAQPage"' in home
    for tag in ["og:title", "og:description", "og:image", "twitter:card",
                "twitter:title", "twitter:description", 'rel="canonical"']:
        assert tag in home, tag
    r = c.get("/robots.txt")
    assert r.status_code == 200 and "Allow: /" in r.get_data(as_text=True)
    assert "Sitemap:" in r.get_data(as_text=True)
    s = c.get("/sitemap.xml")
    assert s.status_code == 200 and "<urlset" in s.get_data(as_text=True)
    assert c.get("/static/img/og.png").status_code == 200
