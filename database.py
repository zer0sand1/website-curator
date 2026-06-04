import os
import random

DB_URL = os.getenv("DATABASE_URL")
IS_POSTGRES = bool(DB_URL)

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import sqlite3

def connect():
    if IS_POSTGRES:
        return psycopg2.connect(DB_URL)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        conn = sqlite3.connect(os.path.join(base, "curator.db"))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

def _fetchone(conn, sql, params=None):
    if IS_POSTGRES:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None
    else:
        cur = conn.execute(sql, params or ())
        row = cur.fetchone()
        return dict(row) if row else None

def _fetchall(conn, sql, params=None):
    if IS_POSTGRES:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return [dict(r) for r in cur.fetchall()]
    else:
        cur = conn.execute(sql, params or ())
        return [dict(r) for r in cur.fetchall()]

def _execute(conn, sql, params=None):
    if IS_POSTGRES:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
    else:
        conn.execute(sql, params or ())
        conn.commit()

def init_tables(conn):
    if IS_POSTGRES:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS websites (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                note TEXT,
                rated_at TIMESTAMP,
                sort_order REAL NOT NULL DEFAULT 0.5
            )
        """)
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                note TEXT,
                rated_at TIMESTAMP,
                sort_order REAL NOT NULL DEFAULT 0.5
            )
        """)
    conn.commit()

def seed_urls(conn, urls_path):
    with open(urls_path) as f:
        urls = [line.strip() for line in f if line.strip()]

    existing = set()
    for row in _fetchall(conn, "SELECT url FROM websites"):
        existing.add(row["url"])

    new_urls = [(u,) for u in urls if u not in existing]
    if new_urls:
        if IS_POSTGRES:
            for u in new_urls:
                _execute(conn, "INSERT INTO websites (url, status) VALUES (%s, 'pending') ON CONFLICT (url) DO NOTHING", u)
        else:
            conn.executemany("INSERT OR IGNORE INTO websites (url, status) VALUES (?, 'pending')", new_urls)
            conn.commit()

    ids = [row["id"] for row in _fetchall(conn, "SELECT id FROM websites WHERE status = 'pending'")]
    random.shuffle(ids)
    for i, wid in enumerate(ids):
        sort_val = i / max(len(ids), 1)
        _execute(conn, "UPDATE websites SET sort_order = %s WHERE id = %s" if IS_POSTGRES else "UPDATE websites SET sort_order = ? WHERE id = ?",
                 (sort_val, wid))

def next_pending(conn, exclude_id=None):
    if IS_POSTGRES:
        sql = "SELECT id, url FROM websites WHERE status = 'pending'"
        params = []
        if exclude_id:
            sql += " AND id != %s"
            params.append(exclude_id)
        sql += " ORDER BY sort_order LIMIT 1"
    else:
        sql = "SELECT id, url FROM websites WHERE status = 'pending'"
        params = []
        if exclude_id:
            sql += " AND id != ?"
            params.append(exclude_id)
        sql += " ORDER BY sort_order LIMIT 1"
    return _fetchone(conn, sql, tuple(params))

def rate_site(conn, site_id, status, note):
    from datetime import datetime
    if IS_POSTGRES:
        _execute(conn, "UPDATE websites SET status = %s, note = %s, rated_at = %s WHERE id = %s",
                 (status, note if note else None, datetime.utcnow().isoformat(), site_id))
    else:
        _execute(conn, "UPDATE websites SET status = ?, note = ?, rated_at = ? WHERE id = ?",
                 (status, note if note else None, datetime.utcnow().isoformat(), site_id))

def get_site(conn, site_id):
    if IS_POSTGRES:
        return _fetchone(conn, "SELECT id, url, status, note FROM websites WHERE id = %s", (site_id,))
    else:
        return _fetchone(conn, "SELECT id, url, status, note FROM websites WHERE id = ?", (site_id,))

def liked_sites(conn):
    return _fetchall(conn, "SELECT id, url, note, rated_at FROM websites WHERE status = 'liked' ORDER BY rated_at DESC")

def get_stats(conn):
    if IS_POSTGRES:
        total = _fetchone(conn, "SELECT COUNT(*) as cnt FROM websites")["cnt"]
        reviewed = _fetchone(conn, "SELECT COUNT(*) as cnt FROM websites WHERE status != 'pending'")["cnt"]
        pending = _fetchone(conn, "SELECT COUNT(*) as cnt FROM websites WHERE status = 'pending'")["cnt"]
        liked = _fetchone(conn, "SELECT COUNT(*) as cnt FROM websites WHERE status = 'liked'")["cnt"]
    else:
        total = _fetchone(conn, "SELECT COUNT(*) as cnt FROM websites")["cnt"]
        reviewed = _fetchone(conn, "SELECT COUNT(*) as cnt FROM websites WHERE status != 'pending'")["cnt"]
        pending = _fetchone(conn, "SELECT COUNT(*) as cnt FROM websites WHERE status = 'pending'")["cnt"]
        liked = _fetchone(conn, "SELECT COUNT(*) as cnt FROM websites WHERE status = 'liked'")["cnt"]
    return {"total": total, "reviewed": reviewed, "pending": pending, "liked": liked}
