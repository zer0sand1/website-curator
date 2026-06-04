import sqlite3
import os
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "curator.db")
URLS_PATH = os.path.join(os.path.dirname(__file__), "urls.txt")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")
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

with open(URLS_PATH) as f:
    urls = [line.strip() for line in f if line.strip()]

existing = set(row[0] for row in conn.execute("SELECT url FROM websites").fetchall())
new_urls = [(u,) for u in urls if u not in existing]

if new_urls:
    conn.executemany("INSERT OR IGNORE INTO websites (url, status) VALUES (?, 'pending')", new_urls)

# Assign random sort_order to all pending sites (shuffles order)
ids = [row[0] for row in conn.execute("SELECT id FROM websites WHERE status = 'pending'").fetchall()]
random.shuffle(ids)
for i, wid in enumerate(ids):
    conn.execute("UPDATE websites SET sort_order = ? WHERE id = ?", (i / max(len(ids), 1), wid))

conn.commit()
count = conn.execute("SELECT COUNT(*) FROM websites").fetchone()[0]
pending = conn.execute("SELECT COUNT(*) FROM websites WHERE status = 'pending'").fetchone()[0]
print(f"Database has {count} URLs ({pending} pending, {count - pending} rated)")

conn.close()
