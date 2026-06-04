import sqlite3
import os
import random
import urllib.request
from urllib.parse import urlparse
from datetime import datetime
from flask import Flask, jsonify, render_template, request, g, Response

app = Flask(__name__)

BASE = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE, "curator.db")
URLS_PATH = os.path.join(BASE, "urls.txt")

def init_db():
    needs_seed = not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0
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
    if needs_seed and os.path.exists(URLS_PATH):
        with open(URLS_PATH) as f:
            urls = [line.strip() for line in f if line.strip()]
        existing = set(row[0] for row in conn.execute("SELECT url FROM websites").fetchall())
        new_urls = [(u,) for u in urls if u not in existing]
        if new_urls:
            conn.executemany("INSERT OR IGNORE INTO websites (url, status) VALUES (?, 'pending')", new_urls)
        ids = [row[0] for row in conn.execute("SELECT id FROM websites WHERE status = 'pending'").fetchall()]
        random.shuffle(ids)
        for i, wid in enumerate(ids):
            conn.execute("UPDATE websites SET sort_order = ? WHERE id = ?", (i / max(len(ids), 1), wid))
        conn.commit()
    conn.close()

init_db()

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/next")
def next_website():
    exclude = request.args.get("exclude", type=int)
    db = get_db()
    query = "SELECT id, url FROM websites WHERE status = 'pending'"
    params = []
    if exclude:
        query += " AND id != ?"
        params.append(exclude)
    query += " ORDER BY sort_order LIMIT 1"
    row = db.execute(query, params).fetchone()
    if row:
        return jsonify({"id": row["id"], "url": row["url"]})
    return jsonify({"id": None, "url": None})

@app.route("/api/stats")
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM websites").fetchone()[0]
    reviewed = db.execute("SELECT COUNT(*) FROM websites WHERE status != 'pending'").fetchone()[0]
    pending = db.execute("SELECT COUNT(*) FROM websites WHERE status = 'pending'").fetchone()[0]
    liked = db.execute("SELECT COUNT(*) FROM websites WHERE status = 'liked'").fetchone()[0]
    return jsonify({"total": total, "reviewed": reviewed, "pending": pending, "liked": liked})

@app.route("/api/site/<int:site_id>")
def get_site(site_id):
    db = get_db()
    row = db.execute(
        "SELECT id, url, status, note FROM websites WHERE id = ?", (site_id,)
    ).fetchone()
    if row:
        return jsonify(dict(row))
    return jsonify({"error": "not found"}), 404

@app.route("/api/rate", methods=["POST"])
def rate():
    data = request.get_json()
    website_id = data["id"]
    status = data["status"]
    note = data.get("note", "").strip()

    db = get_db()
    db.execute(
        "UPDATE websites SET status = ?, note = ?, rated_at = ? WHERE id = ?",
        (status, note if note else None, datetime.utcnow().isoformat(), website_id),
    )
    db.commit()

    row = db.execute(
        "SELECT id, url FROM websites WHERE status = 'pending' ORDER BY sort_order LIMIT 1"
    ).fetchone()
    if row:
        return jsonify({"id": row["id"], "url": row["url"]})
    return jsonify({"id": None, "url": None})

@app.route("/api/liked")
def liked_websites():
    db = get_db()
    rows = db.execute(
        "SELECT id, url, note, rated_at FROM websites WHERE status = 'liked' ORDER BY rated_at DESC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/liked")
def liked_page():
    return render_template("liked.html")

@app.route("/proxy")
def proxy():
    url = request.args.get("url", "")
    if not url:
        return "Missing url", 400

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        resp = urllib.request.urlopen(req, timeout=15)
        content = resp.read()
        content_type = resp.headers.get("Content-Type", "")

        if "text/html" in content_type:
            text = content.decode("utf-8", errors="replace")
            base_tag = f'<base href="{url}">'
            text = text.replace("<head>", f"<head>{base_tag}")
            text = text.replace("<HEAD>", f"<HEAD>{base_tag}")
            return text
        return Response(content, mimetype=content_type)
    except Exception as e:
        return str(e), 502


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
