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

def test_quiz_radio_groups():
    import re
    app = create_app()
    c = app.test_client()
    # every question's radios must form exactly ONE group, distinct per question
    for url in ["/lesson/passwords-2fa", "/exams?band=recruit&n=5"]:
        html = c.get(url).get_data(as_text=True)
        sets = re.split(r"<fieldset", html)[1:]
        assert sets, url
        seen = set()
        for fs in sets:
            names = set(re.findall(r'name="(q\d+)"', fs))
            assert len(names) == 1, (url, names)
            assert names.pop() not in seen, url
            seen.update(names)
    # full marks when every answer is right (lesson has answers 0,1,0)
    r = c.post("/lesson/passwords-2fa", data={"q0": "0", "q1": "1", "q2": "0"})
    assert "Passed: 3/3" in r.get_data(as_text=True)

def test_logged_in_exam_banks_xp():
    import html as ihtml
    import json as _json
    import re as _re
    app = create_app()
    c = app.test_client()
    c.post("/signup", data={"username": _handle("xpfriend"), "consent": "yes"})
    page = c.get("/exams?band=recruit&n=5").get_data(as_text=True)
    m = _re.search(r'name="qs" value="(.*?)"\s*/?>', page, _re.S)
    assert m, "hidden qs field missing"
    qs = _json.loads(ihtml.unescape(m.group(1)))
    assert len(qs) == 5
    data = {"qs": _json.dumps(qs), "band": "recruit", "n": "5"}
    for i, q in enumerate(qs):
        data[f"q{i}"] = str(q["answer"])
    r = c.post("/exams", data=data)
    assert "100%" in r.get_data(as_text=True)
    prof = c.get("/profile").get_data(as_text=True)
    assert "60 XP" in prof and "62 coins" in prof, prof[:300]

def test_failed_exam_says_no_xp():
    import json as _json
    app = create_app()
    c = app.test_client()
    c.post("/signup", data={"username": _handle("failnote"), "consent": "yes"})
    page = c.get("/exams?band=recruit&n=5").get_data(as_text=True)
    import html as ihtml
    import re as _re
    qs = _json.loads(ihtml.unescape(_re.search(r'name="qs" value="(.*?)"\s*/?>', page, _re.S).group(1)))
    data = {"qs": _json.dumps(qs), "band": "recruit", "n": "5"}
    for i, q in enumerate(qs):
        data[f"q{i}"] = str((q["answer"] + 1) % len(q["choices"]))
    html = c.post("/exams", data=data).get_data(as_text=True)
    assert "no XP banked" in html
    assert "+60 XP" not in html and "banked" not in html.split("no XP banked")[0][-200:]
    prof = c.get("/profile").get_data(as_text=True)
    assert ">0 XP<" in prof and "50 coins" in prof

def test_start_roadmap():
    app = create_app()
    c = app.test_client()
    html = c.get("/start").get_data(as_text=True)
    assert "Pick your trail" in html
    for t in ["First boot", "Terminal tourist", "Skip the line"]:
        assert t in html
    assert "ch-trail" in html
    assert "/lesson/recruit-checkpoint" in html and "/lab/linux-basics" in html

def test_character_sheet():
    app = create_app()
    c = app.test_client()
    c.post("/signup", data={"username": _handle("sheetbud"), "consent": "yes"})
    html = c.get("/profile").get_data(as_text=True)
    assert "Character sheet" in html
    assert 'viewBox="0 0 64 76"' in html
    assert "Street Awake" in html
    assert "Next title:" in html and "XP to go" in html
    assert "Trophy case" in html and "Flag vault" in html

def test_identity_chip_levels_up():
    app = create_app()
    c = app.test_client()
    c.post("/signup", data={"username": _handle("chipbud"), "consent": "yes"})
    html = c.get("/").get_data(as_text=True)
    assert 'class="btn small who recruit"' in html
    assert html.count("<i></i>") >= 1
