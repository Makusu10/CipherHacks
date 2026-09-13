import json
import os
import sqlite3
from .db import connect, init_db

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def seed():
    init_db()
    con = connect()
    cur_path = os.path.join(BASE, "data", "curriculum.json")
    lessons = load_json(cur_path)
    for l in lessons:
        con.execute(
            """INSERT INTO lessons(slug, band, title, body, xp_reward, coins_reward, quiz_json, is_checkpoint)
               VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(slug) DO UPDATE SET band=excluded.band, title=excluded.title,
               body=excluded.body, xp_reward=excluded.xp_reward, coins_reward=excluded.coins_reward,
               quiz_json=excluded.quiz_json, is_checkpoint=excluded.is_checkpoint""",
            (l["slug"], l["band"], l["title"], l["body"], l.get("xp_reward", 40),
             l.get("coins_reward", 10), json.dumps(l.get("quiz", [])),
             1 if l.get("is_checkpoint") else 0),
        )
    # demo accounts for leaderboard honesty: marked as bots, small xp
    for name, xp, elo in [("marisol_bot", 320, 860), ("jun_bot", 180, 820)]:
        con.execute("INSERT OR IGNORE INTO users(username, xp, coins, elo) VALUES(?,?,?,?)",
                    (name, xp, 60, elo))
    con.commit()
    # refresh levels
    from .leveling import level_from_xp
    for row in con.execute("SELECT id, xp FROM users").fetchall():
        con.execute("UPDATE users SET level=? WHERE id=?", (level_from_xp(row["xp"]), row["id"]))
    con.commit()
    con.close()

if __name__ == "__main__":
    seed()
