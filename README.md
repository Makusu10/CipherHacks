# CipherHacks — practice cybersecurity, honestly

Early prototype. Story-driven skill tree (Recruit → Apex), quizzes with checkpoint gating, scripted terminal labs against fictional targets only, 1v1 arena with ELO, guilds, seasons, daily streak, coins-for-hints.

## Run
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. Signup needs only a handle + consent tick. Admin panel: `/admin?token=change-me-dev-only` (set `ADMIN_TOKEN` in prod).

## What's inside
- `app.py` — Flask factory, XP/ELO, gating, scripted terminal API, battles, guilds
- `data/curriculum.json` — 11 lessons (Recruit→Analyst full), checkpoints
- `data/terminal_scenarios.json` — 3 scripted labs (no containers yet)
- `templates/` + `static/` — hand CSS/JS, zero third-party embeds, zero analytics
- Legal: `/privacy /terms /cookies /refunds /conduct /about` + consent banner + form consent + one-click delete

## Compliance notes (don't skip before launch)
- Only handle + progress stored. No email, no trackers. Cookie banner covers the single session cookie.
- No fake reviews, no rank claims, no stock images (CSS only).
- Business info is placeholder (solo dev, no DTI/BIR yet) — see `/about`. Must register before charging.
- PH law: Data Privacy Act 2012 respected (access/delete); Cybercrime RA 10175 cited in Terms; refunds page states free-only.
- Accessibility: skip link, labels, focus ring, 7:1+ contrast, keyboard terminal, no autoplay.

## Roadmap
1. Tiers 1–3 + arena (this build)
2. Real-time duels via websockets
3. More scripted labs → ephemeral Docker sandboxes behind a queue
4. Guild co-op, prestige monthly pool
