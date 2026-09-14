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

# Postgres DDL for true persistence on Vercel (DATABASE_URL / POSTGRES_URL).
# Kept in sync with SCHEMA above: same tables, same UNIQUEs.
SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS users(
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  xp INTEGER NOT NULL DEFAULT 0,
  coins INTEGER NOT NULL DEFAULT 50,
  level INTEGER NOT NULL DEFAULT 1,
  elo INTEGER NOT NULL DEFAULT 800,
  streak INTEGER NOT NULL DEFAULT 0,
  last_active TEXT,
  prestige INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS lessons(
  id SERIAL PRIMARY KEY,
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
  awarded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, code)
);
CREATE TABLE IF NOT EXISTS guilds(
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  motto TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS guild_members(
  guild_id INTEGER NOT NULL REFERENCES guilds(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  UNIQUE(guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS battles(
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  opponent TEXT NOT NULL,
  user_score INTEGER NOT NULL,
  opp_score INTEGER NOT NULL,
  elo_delta INTEGER NOT NULL,
  played_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS flags(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  lab_id TEXT NOT NULL,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, lab_id)
);
CREATE TABLE IF NOT EXISTS daily_completions(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day TEXT NOT NULL,
  completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, day)
);
"""


def database_url():
    return (getattr(config, "DATABASE_URL", "") or "").strip()


def use_postgres():
    return bool(database_url())


def _pg_dsn():
    dsn = database_url()
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    return dsn


class _PgCursor:
    """Wraps a RealDictCursor to look like sqlite3.Cursor for our queries."""

    def __init__(self, cur):
        self._cur = cur
        self.lastrowid = None

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]

    def __getattr__(self, name):
        return getattr(self._cur, name)


class _PgConn:
    """Minimal sqlite3-compatible wrapper around a psycopg2 connection."""

    def __init__(self, pg_conn):
        self._con = pg_conn
        # marker so app.get_db() knows NOT to set sqlite row_factory
        self.is_postgres = True

    def execute(self, sql, params=()):
        import psycopg2.extras  # deferred so SQLite installs don't need it

        q = sql.replace("?", "%s")
        upper = q.lstrip().upper()
        need_returning = (
            upper.startswith("INSERT")
            and "RETURNING" not in upper
        )
        if need_returning:
            q = q.rstrip().rstrip(";") + " RETURNING id"
        cur = self._con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(q, params)
        except Exception as e:
            # Re-raise unique violations as sqlite3.IntegrityError so the
            # app's existing `except sqlite3.IntegrityError` keeps working.
            try:
                import psycopg2.errors as _pg_errors
                import psycopg2 as _pg

                if isinstance(e, (_pg.IntegrityError, _pg_errors.UniqueViolation)):
                    raise sqlite3.IntegrityError(str(e)) from e
            except sqlite3.IntegrityError:
                raise
            except Exception:
                pass
            raise
        wrapped = _PgCursor(cur)
        if need_returning:
            try:
                row = cur.fetchone()
                if row and "id" in row:
                    wrapped.lastrowid = row["id"]
            except Exception:
                wrapped.lastrowid = None
        return wrapped

    def executescript(self, sql):
        # psycopg2 executes multi-statement strings fine.
        cur = self._con.cursor()
        cur.execute(sql)
        cur.close()

    def commit(self):
        self._con.commit()

    def rollback(self):
        try:
            self._con.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._con.close()
        except Exception:
            pass


def connect():
    if use_postgres():
        import psycopg2

        dsn = _pg_dsn()
        # Neon / Vercel Postgres require SSL; add it when missing.
        if "sslmode" not in dsn:
            sep = "&" if "?" in dsn else "?"
            dsn = dsn + sep + "sslmode=require"
        pg = psycopg2.connect(dsn, connect_timeout=10)
        pg.autocommit = False
        return _PgConn(pg)
    parent = os.path.dirname(os.path.abspath(config.DB_PATH))
    if parent:
        os.makedirs(parent, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    con = connect()
    try:
        if getattr(con, "is_postgres", False):
            con.executescript(SCHEMA_PG)
        else:
            con.executescript(SCHEMA)
        con.commit()
    finally:
        con.close()
