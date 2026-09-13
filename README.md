# CipherHacks — practice cybersecurity

A free-first, story-driven cybersecurity playground. Work six case files from
Recruit (passwords, phishing) to Apex (timed boss battle + blue-team triage),
typing real commands into scripted practice boxes. No real targets, no card,
no trackers. Guests can try cards, exams, lessons, and terminals with zero
signup; a free handle only saves XP, flags, ELO, and guilds.

**You get:** 29 lessons with checkpoint gating, 70+ quiz + card prompts, exam
builder, 8 scripted terminal labs, 1v1 arena with ELO, 4 season ladders (XP,
flag hunters, duelists, guilds), guild hall, daily streak, coins-for-hints
shop (priced by band), rank titles (Street Awake → Apex Myth), Prestige at
level 100, and a pixel-arcade interface with hand-drawn art.

---

## 1. What you need (5 minutes)

1. **A computer** — Windows 10/11, macOS, or Linux. Any laptop from the last
   8 years works. No GPU needed.
2. **Python 3.11 or newer.** Check if you already have it:
   - Windows (PowerShell): `python --version`
   - macOS / Linux (Terminal): `python3 --version`
   - You want an answer like `Python 3.13.x`. If you see an error or a
     version below 3.11, install fresh from **python.org → Downloads** and,
     on Windows, tick **“Add python.exe to PATH”** during setup. Then close
     and reopen your terminal.
3. **Git** (to copy the project). Check with `git --version`. Missing it?
   Install from **git-scm.com/downloads**, accept the defaults, reopen the
   terminal.
4. **A browser** — Chrome, Edge, or Firefox, current version.

That is everything. No Docker, no database server, no API keys.

## 2. Copy the project

Open your terminal (Windows: press `Win`, type `PowerShell`, hit Enter;
macOS: Spotlight → `Terminal`) and run these one at a time:

```powershell
# 1. Go somewhere you keep projects (example for Windows)
cd "$HOME\Documents"

# 2. Download CipherHacks
git clone https://github.com/Makusu10/CipherHacks.git

# 3. Step inside it
cd CipherHacks
```

macOS / Linux use the same commands with `python3`/`pip3` where noted below.

## 3. Install and run (2 minutes)

```powershell
# 4. Install the two Python packages it needs (Flask + pytest)
pip install -r requirements.txt

# 5. Start the site
python app.py
```

Leave that window open — it is your server now. You should see something
like `* Running on http://127.0.0.1:5000`. If Windows Firewall asks, allow
private networks only.

```powershell
# If `python` does not work on your machine, try:
python3 app.py
```

## 4. Open it in your browser

Go to **http://127.0.0.1:5000**. You will land on a pixel-art night city
with a live terminal you can type in immediately — no account needed.

**Try this 3-minute tour (no signup):**

1. **Type in the hero box:** `help`, then `ls -la`, then
   `cat readme.txt`. It answers like a tiny Linux machine.
2. **Cards:** click **Cards** → flip with mouse or `Enter`, mark
   Got / Missed. Misses pile into your weak list.
3. **Exam:** click **Exams** → keep All bands, 10 questions → submit.
   Score shows; nothing is saved yet. Banked only at 70%+ with a handle —
   fails say so plainly instead of promising XP.
4. **Lab:** click **Labs** → `linux-basics` → run
   `cat /home/recruit/flag.txt`. You found a flag — it banks only with a
   handle (next step).
5. **Cases:** click **Cases** → read Case 01 → open any Recruit file.

**Save progress (still free):** click **Start practicing**, pick a handle
(3–24 letters/numbers/`_`/`-`, e.g. `quiet_packet`), tick the consent box,
done. Now XP, coins, badges, flags, ELO, and guilds stick. Log out from the
nav on shared PCs.

## 5. What to do next (the game)

| Want… | Go to | Notes |
|---|---|---|
| Follow the story | `/missions` | 6 cases, 29 files, checkpoints gate bands |
| See your character | `/dashboard` | Rank title, XP bar, visual skill map |
| Crack boxes | `/labs` | 8 sims; hints priced by band (1x → 2.5x) |
| Duel | `/arena` | 5 questions vs sparring bot, ELO, 5:00 clock |
| Hunt flags async | `/leaderboards` → Flag hunters | Every `flag{...}` counts |
| Crew up | `/guilds` | Found or join; XP pools by season |
| Streak | `/daily` | One question a day, +30 XP |
| Add lessons | `/admin?token=…` | Needs `ADMIN_TOKEN` (below) |

Level bands: Recruit 1–10 (quiz only, no terminal) → Operator 11–25
(terminal unlocks) → Analyst 26–45 → Specialist 46–70 → Red Team 71–90 →
Apex 91–100. Doors need XP **plus** the previous checkpoint — grinding easy
quizzes cannot skip you. Prestige at 100 resets to 1 with a badge + monthly
rotator pool.

Scoring is honest everywhere: lessons, exams, and checkpoints bank XP only
at 70%+. Fail screens say “no XP banked” outright — never a reward message
for a failing score.

## 6. Stop and restart

- **Stop:** focus the server window, press `Ctrl + C`. Or close the window.
- **Restart:** `cd CipherHacks` then `python app.py` again.
- Your accounts live in `cipherhacks.db` in that folder. Delete the file for
  a fresh world (handles, XP, guilds all reset).

## 7. Run the tests (optional, 30 seconds)

```powershell
python -m pytest tests/ -q
```

10 tests should pass: health, gating, blocked-command guard, guest-first
access, full 1–100 ladder, game layer (ranks, cases, boards), grader SEO
checks (words, FAQ, meta, robots, sitemap), quiz radio groups, logged-in
exam XP banking, and fail-state honesty.

## 8. Admin panel (optional)

Teachers / contributors can add lessons without redeploying:

```powershell
# Windows example — set a secret token for this session, then run
$env:ADMIN_TOKEN = "pick-a-long-random-string"
python app.py
```

Open `http://127.0.0.1:5000/admin?token=pick-a-long-random-string`.
Quiz JSON looks like
`[{"q":"…?","choices":["a","b"],"answer":0}]`. Keep every target fictional.

## 9. Troubleshooting for beginners

| Symptom | Fix |
|---|---|
| `python` is not recognized | Reinstall Python with “Add to PATH” ticked, reopen terminal |
| `pip` not found | Try `python -m pip install -r requirements.txt` |
| Port 5000 busy | Another copy is running: close it, or run `python app.py --port 5050` (Flask flag varies) — simplest is closing the old window |
| Page looks unstyled | Hard-refresh: `Ctrl + F5`. CSS/JS are local files, no CDN needed |
| `git clone` fails | Check internet; confirm URL `https://github.com/Makusu10/CipherHacks.git` |
| Forgot your handle | Handles list lives in `cipherhacks.db`; easiest is signing up fresh — prototype, no recovery mail by design |
| Antivirus complains | It is plain Flask with no binaries; allow the folder or move it out of synced cloud drives |

## 10. Project map (where things live)

```
app.py                 Flask site: XP/ELO, gating, scripted terminal, battles, guilds
config.py              DB path, SECRET_KEY, ADMIN_TOKEN (env-overridable)
data/curriculum.json   29 lessons across 6 bands + 6 checkpoints
data/terminal_scenarios.json  8 scripted labs, flags, hint ladders, cost multipliers
utils/leveling.py      XP curve, bands, ELO math, rank titles, case dossiers
utils/db.py · utils/seed.py  SQLite schema + idempotent seed (lessons, demo bots)
templates/             Pages: map, cases, cards, exams, labs, arena, ladders, guilds, legal
static/css/style.css   Hand CSS, pixel arcade nav, case-file hero, quest log, game boards (no frameworks)
static/js/             app.js (consent), pixel.js (mascot, typing teaser)
static/img/            logo.svg + favicon.svg + og.png, all hand-made (no stock)
robots/sitemap         /robots.txt + /sitemap.xml routes; JSON-LD (Organization,
                       WebSite, Course, FAQPage) + canonical/OG tags in base.html
tests/                 10 pytest checks
```

## 11. Safety, privacy, honesty (read before teaching others)

- **Fictional targets only.** Every technique runs against invented boxes we
  ship (`recruit-box`, `10.13.0.5`, Alon Freight…). Real networks are out of
  scope; abuse gets handles banned. See `/conduct`.
- **Minimal data.** Handle + progress only. One session cookie, no analytics,
  no ads, no external embeds. One-click delete on `/profile`. PH Data Privacy
  Act 2012 respected; Cybercrime RA 10175 cited in Terms.
- **No hype.** No fake reviews, no “#1” claims, no stock art (all visuals are
  hand-made SVG/CSS), no payments — `/refunds` says free-only.
- **Prototype limits.** Scripted labs teach patterns, not live networks.
  Handle login has no password by design for speed — never reuse a real
  password as a handle.

## 12. Roadmap

1. ✅ Bands 1–100 + scripted labs + sparring arena (this repo now)
2. Realtime duels via websockets (server-authoritative)
3. Ephemeral Docker sandboxes replacing scripts behind a queue
4. Guild co-op missions, prestige monthly pool rotation

Issues and ideas belong on GitHub. Solo dev, PH — be kind in the queue.
