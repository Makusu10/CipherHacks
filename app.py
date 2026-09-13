import json
import os
import random
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

import config
from utils.db import connect, init_db
from utils.leveling import (
    BANDS, CHECKPOINT_FOR_BAND, band_for_level, band_label,
    elo_delta, level_from_xp,
)

BAND_ORDER = [b[0] for b in BANDS]

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False  # set True behind HTTPS in prod

    init_db()
    # seed on boot (idempotent)
    try:
        from utils.seed import seed as run_seed
        run_seed()
    except Exception:
        pass

    def get_db():
        if "db" not in g:
            g.db = connect()
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_e=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def current_user():
        uid = session.get("uid")
        if not uid:
            return None
        con = get_db()
        return con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    def login_required(fn):
        @wraps(fn)
        def wrap(*a, **k):
            if not current_user():
                return redirect(url_for("login", next=request.path))
            return fn(*a, **k)
        return wrap

    def completed_slugs(uid):
        con = get_db()
        rows = con.execute("SELECT lesson_slug FROM progress WHERE user_id=? AND completed=1", (uid,)).fetchall()
        return {r["lesson_slug"] for r in rows}

    def can_access_band(uid, band):
        idx = BAND_ORDER.index(band)
        if idx == 0:
            return True
        done = completed_slugs(uid)
        for prev in BAND_ORDER[:idx]:
            cp = CHECKPOINT_FOR_BAND.get(prev)
            if cp and cp not in done:
                return False
        return True

    def award_xp(uid, xp, coins=0):
        con = get_db()
        u = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        nxp = u["xp"] + xp
        ncoins = u["coins"] + coins
        lvl = level_from_xp(nxp)
        today = date.today().isoformat()
        streak = u["streak"] or 0
        if u["last_active"] != today:
            yesterday = date.today().toordinal() - 1
            try:
                last = date.fromisoformat(u["last_active"]).toordinal() if u["last_active"] else None
            except Exception:
                last = None
            streak = streak + 1 if last == yesterday else 1
        con.execute("UPDATE users SET xp=?, coins=?, level=?, streak=?, last_active=? WHERE id=?",
                    (nxp, ncoins, lvl, streak, today, uid))
        con.commit()
        check_badges(uid)
        return lvl

    def give_badge(uid, code):
        con = get_db()
        try:
            con.execute("INSERT INTO badges(user_id, code) VALUES(?,?)", (uid, code))
            con.commit()
        except sqlite3.IntegrityError:
            pass

    def check_badges(uid):
        con = get_db()
        done = completed_slugs(uid)
        n = len(done)
        if n >= 1:
            give_badge(uid, "first-step")
        if n >= 5:
            give_badge(uid, "steady-5")
        u = con.execute("SELECT streak FROM users WHERE id=?", (uid,)).fetchone()
        if u and u["streak"] >= 3:
            give_badge(uid, "streak-3")
        if any(s.endswith("-checkpoint") for s in done):
            give_badge(uid, "gate-crasher")
        nf = con.execute("SELECT COUNT(*) c FROM flags WHERE user_id=?", (uid,)).fetchone()["c"]
        if nf >= 1:
            give_badge(uid, "flag-hunter")
        nb = con.execute("SELECT COUNT(*) c FROM battles WHERE user_id=?", (uid,)).fetchone()["c"]
        if nb >= 1:
            give_badge(uid, "duelist")

    def all_lessons():
        con = get_db()
        return con.execute("SELECT * FROM lessons ORDER BY id").fetchall()

    def scenarios():
        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, "data", "terminal_scenarios.json"), encoding="utf-8") as f:
            return json.load(f)

    @app.context_processor
    def inject_user():
        return {"me": current_user(), "band_label": band_label}

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/healthz")
    def healthz():
        return jsonify(ok=True)

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        err = None
        if request.method == "POST":
            handle = (request.form.get("username") or "").strip().lower()[:24]
            consent = request.form.get("consent")
            if len(handle) < 3 or not handle.replace("_", "").replace("-", "").isalnum():
                err = "Pick a handle with 3-24 letters, numbers, _ or -."
            elif not consent:
                err = "Please tick the consent box so we can store your progress."
            else:
                con = get_db()
                try:
                    cur = con.execute("INSERT INTO users(username) VALUES(?)", (handle,))
                    con.commit()
                    session["uid"] = cur.lastrowid
                    return redirect(url_for("dashboard"))
                except sqlite3.IntegrityError:
                    err = "That handle is taken. Try a variant."
        return render_template("signup.html", err=err)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        err = None
        if request.method == "POST":
            handle = (request.form.get("username") or "").strip().lower()
            con = get_db()
            u = con.execute("SELECT * FROM users WHERE username=?", (handle,)).fetchone()
            if not u:
                err = "No such handle yet. Sign up first."
            else:
                session["uid"] = u["id"]
                nxt = request.args.get("next") or url_for("dashboard")
                return redirect(nxt)
        return render_template("login.html", err=err)

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        me = current_user()
        lessons = all_lessons()
        done = completed_slugs(me["id"])
        tree = []
        for les in lessons:
            locked = not can_access_band(me["id"], les["band"])
            tree.append({"les": les, "done": les["slug"] in done, "locked": locked})
        con = get_db()
        badges = con.execute("SELECT code FROM badges WHERE user_id=?", (me["id"],)).fetchall()
        return render_template("dashboard.html", tree=tree, badges=[b["code"] for b in badges], me=me)

    @app.route("/lesson/<slug>", methods=["GET", "POST"])
    @login_required
    def lesson(slug):
        me = current_user()
        con = get_db()
        les = con.execute("SELECT * FROM lessons WHERE slug=?", (slug,)).fetchone()
        if not les:
            return render_template("error.html", msg="Lesson not found."), 404
        if not can_access_band(me["id"], les["band"]):
            return render_template("error.html", msg="Locked. Clear the previous band checkpoint first."), 403
        quiz = json.loads(les["quiz_json"] or "[]")
        result = None
        if request.method == "POST":
            score = 0
            for i, item in enumerate(quiz):
                try:
                    picked = int(request.form.get(f"q{i}", "-1"))
                except ValueError:
                    picked = -1
                if picked == item.get("answer"):
                    score += 1
            pct = round(100 * score / max(1, len(quiz)))
            passed = pct >= 70
            first = con.execute("SELECT * FROM progress WHERE user_id=? AND lesson_slug=?",
                                (me["id"], slug)).fetchone()
            if passed and (not first or not first["completed"]):
                award_xp(me["id"], les["xp_reward"], les["coins_reward"])
                con.execute("""INSERT INTO progress(user_id, lesson_slug, completed, score, completed_at)
                               VALUES(?,?,?,?,?) ON CONFLICT(user_id, lesson_slug) DO UPDATE SET
                               completed=1, score=excluded.score, completed_at=excluded.completed_at""",
                            (me["id"], slug, pct, datetime.utcnow().isoformat()))
                con.commit()
            result = {"score": score, "total": len(quiz), "pct": pct, "passed": passed}
            me = current_user()
        # hint ladder (3 tiers, escalating cost)
        hints = []
        try:
            sc = scenarios()
            # map lesson slug to lab for hint display on linked labs
            lab_map = {"linux-first-steps": "linux-basics", "osint-footprinting": "scan-sim",
                       "owasp-sqli-xss": "scan-sim", "ports-protocols": "scan-sim"}
            lab = lab_map.get(slug)
            if lab and lab in sc:
                hints = sc[lab]["hints"]
        except Exception:
            hints = []
        return render_template("lesson.html", les=les, quiz=quiz, result=result, hints=hints, me=me)

    # ---- labs / scripted terminal ----
    @app.route("/labs")
    @login_required
    def labs():
        return render_template("labs.html", scenarios=scenarios(), me=current_user())

    @app.route("/lab/<lab_id>")
    @login_required
    def lab(lab_id):
        sc = scenarios()
        if lab_id not in sc:
            return render_template("error.html", msg="Lab not found."), 404
        return render_template("lab.html", lab_id=lab_id, lab=sc[lab_id], me=current_user())

    def terminal_reply(lab_id, cmd):
        sc = scenarios()[lab_id]
        c = cmd.strip()
        if not c:
            return ""
        lc = c.lower()
        if lc in ("help", "?"):
            return "commands: help, pwd, ls, ls -la, cat <file>, scan <ip>, probe --web, crack --wordlist words.txt hash.txt, submit flag{...}, clear"
        if lc == "pwd":
            return "/home/recruit" if lab_id == "linux-basics" else "/home/analyst"
        if lc in ("ls", "dir"):
            if lab_id == "linux-basics":
                return "readme.txt  missions/"
            if lab_id == "scan-sim":
                return "vuln.txt  notes.txt"
            return "hash.txt  words.txt  crack"
        if lc == "ls -la":
            if lab_id == "linux-basics":
                return "total 12\n-rw-r--r-- 1 you you 68 readme.txt\n-rw-r--r-- 1 you you 41 .note\ndrwxr-xr-x 2 you you 4096 missions/"
            return "total 12\n-rw-r--r-- 1 you you 52 hash.txt\n-rw-r--r-- 1 you you 28 words.txt"
        if lc.startswith("cat "):
            name = c[4:].strip().strip("'\"")
            files = sc.get("files", {})
            if name in files:
                return files[name]
            if name in ("readme.txt", ".note", "vuln.txt", "notes.txt", "hash.txt", "words.txt"):
                return files.get(name, "empty file")
            if name == "/home/recruit/flag.txt":
                return files.get("/home/recruit/flag.txt", "no such file")
            if name in ("missions/brief.txt",):
                return "Brief: practice only. Targets here are fictional."
            return f"cat: {name}: no such file"
        if lc.startswith("scan "):
            if lab_id != "scan-sim":
                return "scan: not installed on this box. Try ls."
            return "PORT     STATE  SERVICE\n22/tcp   closed ssh\n80/tcp   open   http\n443/tcp  closed https\n-- 1 host up, fictional target 10.13.0.5"
        if lc == "probe --web":
            if lab_id != "scan-sim":
                return "probe: nothing to probe here."
            return "GET /login 200 — form field 'user' looks concatenated into SQL. Saved evidence. See vuln.txt."
        if lc.startswith("crack"):
            if lab_id != "hash-drill":
                return "crack: no hashes on this box."
            if "words.txt" in lc and "hash.txt" in lc:
                return "tried 4 candidates... HIT: 'hello' matches 5d41402abc4b2a76b9719d911017c592\nsubmit flag{hello_cracked}"
            return "usage: crack --wordlist words.txt hash.txt"
        if lc.startswith("submit "):
            return "Use the flag box under the terminal to submit."
        if lc == "whoami":
            return "recruit"
        if lc == "clear":
            return "__clear__"
        if c.startswith("flag{"):
            return "Use the flag box under the terminal to submit."
        return f"{c.split()[0]}: command not found (practice box, try 'help')"

    @app.route("/api/terminal", methods=["POST"])
    @login_required
    def api_terminal():
        data = request.get_json(force=True, silent=True) or {}
        lab_id = data.get("lab_id", "")
        cmd = (data.get("cmd", "") or "")[:500]
        if lab_id not in scenarios():
            return jsonify(output="unknown lab"), 404
        # hard block: never allow real-target syntax
        banned = ["ssh ", "curl http", "wget http", "nmap ", "; rm", "telnet "]
        if any(b in cmd.lower() for b in banned):
            return jsonify(output="Blocked: practice box only. No real hosts, no exfil-style commands.")
        return jsonify(output=terminal_reply(lab_id, cmd))

    @app.route("/api/flag", methods=["POST"])
    @login_required
    def api_flag():
        me = current_user()
        data = request.get_json(force=True, silent=True) or {}
        lab_id = data.get("lab_id", "")
        flag = (data.get("flag", "") or "").strip()
        sc = scenarios()
        if lab_id not in sc:
            return jsonify(ok=False, msg="unknown lab"), 404
        if flag in sc[lab_id].get("flags", []):
            con = get_db()
            try:
                con.execute("INSERT INTO flags(user_id, lab_id) VALUES(?,?)", (me["id"], lab_id))
                con.commit()
                award_xp(me["id"], 100, 25)
                return jsonify(ok=True, msg="Flag accepted. +100 XP, +25 coins.")
            except sqlite3.IntegrityError:
                return jsonify(ok=True, msg="Already solved. Nice.")
        return jsonify(ok=False, msg="Wrong flag. Check spacing and braces.")

    @app.route("/api/hint", methods=["POST"])
    @login_required
    def api_hint():
        me = current_user()
        data = request.get_json(force=True, silent=True) or {}
        lab_id = data.get("lab_id", "")
        tier = int(data.get("tier", 0))
        costs = [5, 15, 30]
        if lab_id not in scenarios() or tier not in (0, 1, 2):
            return jsonify(ok=False), 400
        cost = costs[tier]
        con = get_db()
        u = con.execute("SELECT coins FROM users WHERE id=?", (me["id"],)).fetchone()
        if u["coins"] < cost:
            return jsonify(ok=False, msg="Not enough coins. Earn XP first."), 402
        con.execute("UPDATE users SET coins=coins-? WHERE id=?", (cost, me["id"]))
        con.commit()
        return jsonify(ok=True, hint=scenarios()[lab_id]["hints"][tier], cost=cost)

    # ---- battle arena (async-simulated 1v1 vs bot) ----
    @app.route("/arena", methods=["GET", "POST"])
    @login_required
    def arena():
        me = current_user()
        con = get_db()
        lessons = con.execute("SELECT quiz_json FROM lessons WHERE is_checkpoint=0").fetchall()
        pool = []
        for r in lessons:
            try:
                pool.extend(json.loads(r["quiz_json"] or "[]"))
            except Exception:
                pass
        questions = random.sample(pool, min(5, len(pool))) if pool else []
        result = None
        if request.method == "POST":
            score = 0
            qs = json.loads(request.form.get("qs", "[]"))
            for i, item in enumerate(qs):
                try:
                    if int(request.form.get(f"q{i}", "-1")) == item.get("answer"):
                        score += 1
                except ValueError:
                    pass
            opp_elo = max(600, min(1400, me["elo"] + random.randint(-120, 120)))
            opp_score = max(0, min(5, round(random.gauss(2.6, 1.1) + (opp_elo - me["elo"]) / 400)))
            if score > opp_score:
                s = 1.0
            elif score == opp_score:
                s = 0.5
            else:
                s = 0.0
            d = elo_delta(me["elo"], opp_elo, s)
            con.execute("UPDATE users SET elo=elo+? WHERE id=?", (d, me["id"]))
            con.execute("INSERT INTO battles(user_id, opponent, user_score, opp_score, elo_delta) VALUES(?,?,?,?,?)",
                        (me["id"], f"rival-{opp_elo}", score, opp_score, d))
            con.commit()
            if s == 1.0:
                award_xp(me["id"], 50, 12)
            check_badges(me["id"])
            me = current_user()
            result = {"you": score, "opp": opp_score, "opp_elo": opp_elo, "delta": d}
            questions = qs
        history = con.execute("SELECT * FROM battles WHERE user_id=? ORDER BY id DESC LIMIT 10", (me["id"],)).fetchall()
        return render_template("arena.html", questions=questions, result=result, history=history, me=me)

    @app.route("/leaderboards")
    def leaderboards():
        con = get_db() if "db" in g or True else connect()
        # ensure db handle
        try:
            db = get_db()
        except RuntimeError:
            db = connect()
        top = db.execute("SELECT username, xp, level, elo FROM users ORDER BY xp DESC LIMIT 20").fetchall()
        guilds = db.execute("""SELECT g.name, COALESCE(SUM(u.xp),0) xp, COUNT(m.user_id) members
                               FROM guilds g LEFT JOIN guild_members m ON m.guild_id=g.id
                               LEFT JOIN users u ON u.id=m.user_id GROUP BY g.id ORDER BY xp DESC LIMIT 10""").fetchall()
        season = date.today().strftime("%Y-%m")
        if db is not connect:
            pass
        return render_template("leaderboards.html", top=top, guilds=guilds, season=season)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        me = current_user()
        con = get_db()
        if request.method == "POST" and request.form.get("action") == "delete":
            con.execute("DELETE FROM users WHERE id=?", (me["id"],))
            con.commit()
            session.clear()
            return redirect(url_for("index"))
        badges = con.execute("SELECT code, awarded_at FROM badges WHERE user_id=?", (me["id"],)).fetchall()
        flags = con.execute("SELECT lab_id, submitted_at FROM flags WHERE user_id=?", (me["id"],)).fetchall()
        prog = con.execute("SELECT COUNT(*) c FROM progress WHERE user_id=? AND completed=1", (me["id"],)).fetchone()["c"]
        gm = con.execute("""SELECT g.name FROM guild_members m JOIN guilds g ON g.id=m.guild_id
                            WHERE m.user_id=?""", (me["id"],)).fetchall()
        # prestige: level 100 resets with badge
        can_prestige = me["level"] >= 100
        if request.method == "POST" and request.form.get("action") == "prestige" and can_prestige:
            con.execute("UPDATE users SET xp=0, level=1, prestige=prestige+1 WHERE id=?", (me["id"],))
            con.execute("DELETE FROM progress WHERE user_id=?", (me["id"],))
            con.commit()
            give_badge(me["id"], f"prestige-{me['prestige']+1}")
            return redirect(url_for("dashboard"))
        return render_template("profile.html", badges=badges, flags=flags, done=prog,
                               guilds=gm, can_prestige=can_prestige, me=current_user())

    @app.route("/daily", methods=["GET", "POST"])
    @login_required
    def daily():
        me = current_user()
        con = get_db()
        today = date.today().isoformat()
        already = con.execute("SELECT 1 FROM daily_completions WHERE user_id=? AND day=?", (me["id"], today)).fetchone()
        # deterministic daily pick
        seed_n = int(date.today().strftime("%Y%m%d"))
        rnd = random.Random(seed_n)
        lessons = con.execute("SELECT quiz_json FROM lessons WHERE is_checkpoint=0").fetchall()
        pool = []
        for r in lessons:
            try:
                pool.extend(json.loads(r["quiz_json"] or "[]"))
            except Exception:
                pass
        q = rnd.choice(pool) if pool else None
        msg = None
        if request.method == "POST" and q and not already:
            try:
                picked = int(request.form.get("q0", "-1"))
            except ValueError:
                picked = -1
            if picked == q.get("answer"):
                award_xp(me["id"], 30, 8)
                con.execute("INSERT INTO daily_completions(user_id, day) VALUES(?,?)", (me["id"], today))
                con.commit()
                msg = "Daily done. +30 XP, streak kept alive."
            else:
                msg = "Not quite. Try again tomorrow — streak only counts wins."
            already = True
        return render_template("daily.html", q=q, already=already, msg=msg, me=current_user())

    @app.route("/flashcards")
    @login_required
    def flashcards():
        con = get_db()
        cards = []
        for r in con.execute("SELECT slug, title, band, quiz_json FROM lessons").fetchall():
            try:
                quiz = json.loads(r["quiz_json"] or "[]")
            except Exception:
                quiz = []
            for i, item in enumerate(quiz):
                choices = item.get("choices", [])
                ans = item.get("answer", 0)
                front = item.get("q", "")
                back = choices[ans] if 0 <= ans < len(choices) else ""
                cards.append({"lesson": r["slug"], "band": r["band"], "front": front,
                              "back": back, "choices": choices})
        random.shuffle(cards)
        return render_template("flashcards.html", cards=cards[:40], me=current_user())

    @app.route("/exams", methods=["GET", "POST"])
    @login_required
    def exams():
        me = current_user()
        con = get_db()
        band = request.values.get("band", "all")
        n = min(20, max(5, int(request.values.get("n", 10) or 10)))
        pool = []
        for r in con.execute("SELECT band, quiz_json FROM lessons").fetchall():
            if band != "all" and r["band"] != band:
                continue
            try:
                pool.extend(json.loads(r["quiz_json"] or "[]"))
            except Exception:
                pass
        questions = random.sample(pool, min(n, len(pool))) if pool else []
        result = None
        if request.method == "POST":
            qs = json.loads(request.form.get("qs", "[]"))
            score = 0
            for i, item in enumerate(qs):
                try:
                    if int(request.form.get(f"q{i}", "-1")) == item.get("answer"):
                        score += 1
                except ValueError:
                    pass
            pct = round(100 * score / max(1, len(qs)))
            if pct >= 70:
                award_xp(me["id"], 60, 12)
                me = current_user()
            result = {"score": score, "total": len(qs), "pct": pct}
            questions = qs
        return render_template("exams.html", questions=questions, result=result,
                               band=band, n=n, me=me)

    @app.route("/guilds", methods=["GET", "POST"])
    @login_required
    def guilds():
        me = current_user()
        con = get_db()
        msg = None
        if request.method == "POST":
            act = request.form.get("action")
            name = (request.form.get("name") or "").strip()[:32]
            if act == "create" and len(name) >= 3:
                try:
                    cur = con.execute("INSERT INTO guilds(name, motto) VALUES(?,?)",
                                      (name, (request.form.get("motto") or "")[:120]))
                    con.execute("INSERT INTO guild_members(guild_id, user_id, role) VALUES(?,?,?)",
                                (cur.lastrowid, me["id"], "captain"))
                    con.commit()
                    msg = f"Guild '{name}' formed. You are captain."
                except sqlite3.IntegrityError:
                    msg = "That guild name is taken."
            elif act == "join" and name:
                grow = con.execute("SELECT id FROM guilds WHERE name=?", (name,)).fetchone()
                if not grow:
                    msg = "No guild by that name."
                else:
                    try:
                        con.execute("INSERT INTO guild_members(guild_id, user_id) VALUES(?,?)",
                                    (grow["id"], me["id"]))
                        con.commit()
                        msg = f"Joined {name}."
                    except sqlite3.IntegrityError:
                        msg = "Already a member."
            elif act == "leave":
                con.execute("DELETE FROM guild_members WHERE user_id=?", (me["id"],))
                con.commit()
                msg = "Left your guild."
        rows = con.execute("""SELECT g.id, g.name, g.motto, COUNT(m.user_id) members,
                              COALESCE(SUM(u.xp),0) xp FROM guilds g
                              LEFT JOIN guild_members m ON m.guild_id=g.id
                              LEFT JOIN users u ON u.id=m.user_id
                              GROUP BY g.id ORDER BY xp DESC""").fetchall()
        mine = con.execute("SELECT g.name FROM guild_members m JOIN guilds g ON g.id=m.guild_id WHERE m.user_id=?",
                           (me["id"],)).fetchone()
        return render_template("guilds.html", guilds=rows, mine=mine["name"] if mine else None, msg=msg, me=me)

    @app.route("/admin", methods=["GET", "POST"])
    def admin():
        if request.args.get("token", "") != config.ADMIN_TOKEN and request.form.get("token", "") != config.ADMIN_TOKEN:
            return render_template("admin_gate.html"), 401
        con = get_db()
        msg = None
        if request.method == "POST" and request.form.get("slug"):
            try:
                quiz = json.loads(request.form.get("quiz_json", "[]"))
            except Exception:
                quiz = []
                msg = "Quiz JSON invalid — saved with empty quiz."
            con.execute("""INSERT INTO lessons(slug, band, title, body, xp_reward, coins_reward, quiz_json, is_checkpoint)
                           VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET band=excluded.band,
                           title=excluded.title, body=excluded.body, xp_reward=excluded.xp_reward,
                           coins_reward=excluded.coins_reward, quiz_json=excluded.quiz_json""",
                        (request.form["slug"].strip().lower(), request.form.get("band", "recruit"),
                         request.form.get("title", "Untitled"), request.form.get("body", ""),
                         int(request.form.get("xp_reward") or 40), int(request.form.get("coins_reward") or 10),
                         json.dumps(quiz), 0))
            con.commit()
            msg = msg or "Lesson saved."
        lessons = con.execute("SELECT slug, band, title FROM lessons ORDER BY id").fetchall()
        return render_template("admin.html", lessons=lessons, msg=msg, token=config.ADMIN_TOKEN if config.ADMIN_TOKEN.startswith("change") else "")

    # ---- legal / static ----
    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/cookies")
    def cookies():
        return render_template("cookies.html")

    @app.route("/refunds")
    def refunds():
        return render_template("refunds.html")

    @app.route("/conduct")
    def conduct():
        return render_template("conduct.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
