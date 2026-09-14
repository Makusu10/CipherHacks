import os
import sqlite3
import config

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  xp INTEGER NOT NULL DEFAULT 0,
  coins INTEGER NOT NULL DEFAULT 50,
  level INTEGER NOT NULL DEFAULT 1,
  elo INTEGER NOT NULL DEFAULT 800,
  streak INTEGER NOT NULL DEFAULT 0,
  last_active TEXT,
  prestige INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS lessons(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  band TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  xp_reward INTEGER NOT NULL DEFAULT 40,
  coins_reward INTEGER NOT NULL DEFAULT 10,
  quiz_json TEXT NOT NULL DEFAULT '[]',
  is_checkpoint INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS progress(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  lesson_slug TEXT NOT NULL,
  completed INTEGER NOT NULL DEFAULT 0,
  score INTEGER NOT NULL DEFAULT 0,
  completed_at TEXT,
  UNIQUE(user_id, lesson_slug)
);
CREATE TABLE IF NOT EXISTS badges(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  awarded_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, code)
);
CREATE TABLE IF NOT EXISTS guilds(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  motto TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS guild_members(
  guild_id INTEGER NOT NULL REFERENCES guilds(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  UNIQUE(guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS battles(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  opponent TEXT NOT NULL,
  user_score INTEGER NOT NULL,
  opp_score INTEGER NOT NULL,
  elo_delta INTEGER NOT NULL,
  played_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS flags(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  lab_id TEXT NOT NULL,
  submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, lab_id)
);
CREATE TABLE IF NOT EXISTS daily_completions(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day TEXT NOT NULL,
  completed_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, day)
);
"""

def connect():
    parent = os.path.dirname(os.path.abspath(config.DB_PATH))
    if parent:
        os.makedirs(parent, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    con = connect()
    con.executescript(SCHEMA)
    con.commit()
    con.close()
