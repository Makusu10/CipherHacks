"""Regression test for the Vercel 'auto logs out + can't log back in' bug.

Root cause: Vercel serverless /tmp SQLite is per-instance and ephemeral.
Signup could land on instance A while the next request hit instance B
(fresh DB) or a cold start wiped the file. The old code stored only
session["uid"], so the row lookup failed -> every page rendered logged-out
and re-login said "No such handle yet".

Fix: sessions store uid + handle (signed cookie survives instances) and
current_user() self-heals (rebind by handle, or re-create the same handle
on a fresh demo DB). Login normalizes and clears stale uids.
"""
import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _fresh_app(monkeypatch=None):
    fd, dbp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(dbp)
    os.environ["CIPHERHACKS_DB"] = dbp
    # ensure postgres mode is off for this test
    for k in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL",
              "POSTGRES_URL_NON_POOLING"):
        os.environ.pop(k, None)
    # re-import config fresh is overkill; create_app reads env via config
    # module attributes set at import — patch them directly.
    import config
    config.DATABASE_URL = ""
    config.DB_PATH = dbp
    from app import create_app
    app = create_app()
    return app, dbp


def test_stale_uid_stays_logged_in_and_relogin_works():
    app, dbp = _fresh_app()
    c = app.test_client()
    handle = "heal_%s" % uuid.uuid4().hex[:8]
    assert c.post("/signup", data={"username": handle, "consent": "yes"}).status_code == 302
    assert "Log out" in c.get("/missions").get_data(as_text=True)

    # Simulate Vercel cold start / other instance: wipe the DB file.
    os.remove(dbp)
    from app import create_app as _mk
    _mk()  # recreates a fresh DB without our user

    # Same session cookie must NOT render logged-out...
    html = c.get("/missions").get_data(as_text=True)
    assert "Log out" in html
    assert ">Log in<" not in html
    # ...login_required pages must not bounce to /login...
    assert c.get("/dashboard").status_code == 200
    # ...and a fresh browser CAN log in with the same handle (healed row).
    c2 = app.test_client()
    r = c2.post("/login", data={"username": handle})
    assert r.status_code == 302, r.get_data(as_text=True)[:500]
    assert "No such handle" not in r.get_data(as_text=True)


def test_login_normalizes_case_and_whitespace():
    app, dbp = _fresh_app()
    c = app.test_client()
    handle = "Case_%s" % uuid.uuid4().hex[:8]
    c.post("/signup", data={"username": handle, "consent": "yes"})
    c2 = app.test_client()
    r = c2.post("/login", data={"username": "  %s  " % handle.upper()})
    assert r.status_code == 302


def test_old_session_without_handle_repairs():
    app, dbp = _fresh_app()
    c = app.test_client()
    handle = "old_%s" % uuid.uuid4().hex[:8]
    c.post("/signup", data={"username": handle, "consent": "yes"})
    with c.session_transaction() as s:
        s.pop("handle", None)
    assert "Log out" in c.get("/missions").get_data(as_text=True)
    with c.session_transaction() as s:
        assert s.get("handle") == handle.lower()[:24]
