import os
from flask import Flask, jsonify, render_template, request, g, Response
import urllib.request
import database as db

app = Flask(__name__)
BASE = os.path.dirname(__file__)

def get_conn():
    if "conn" not in g:
        g.conn = db.connect()
    return g.conn

@app.teardown_appcontext
def close_conn(exception):
    conn = g.pop("conn", None)
    if conn:
        conn.close()

def init_db():
    import os
    conn = db.connect()
    db.init_tables(conn)
    urls_path = os.path.join(BASE, "urls.txt")
    if os.path.exists(urls_path):
        existing = db.get_stats(conn)
        if existing["total"] == 0:
            db.seed_urls(conn, urls_path)
    conn.close()

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/next")
def next_website():
    exclude = request.args.get("exclude", type=int)
    row = db.next_pending(get_conn(), exclude_id=exclude)
    if row:
        return jsonify({"id": row["id"], "url": row["url"]})
    return jsonify({"id": None, "url": None})

@app.route("/api/stats")
def stats():
    return jsonify(db.get_stats(get_conn()))

@app.route("/api/site/<int:site_id>")
def get_site(site_id):
    row = db.get_site(get_conn(), site_id)
    if row:
        return jsonify(row)
    return jsonify({"error": "not found"}), 404

@app.route("/api/rate", methods=["POST"])
def rate():
    data = request.get_json()
    website_id = data["id"]
    status = data["status"]
    note = data.get("note", "").strip()

    db.rate_site(get_conn(), website_id, status, note if note else None)
    row = db.next_pending(get_conn())
    if row:
        return jsonify({"id": row["id"], "url": row["url"]})
    return jsonify({"id": None, "url": None})

@app.route("/api/liked")
def liked_websites():
    return jsonify(db.liked_sites(get_conn()))

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
            text = text.replace("<head>", f"<head><base href=\"{url}\">")
            text = text.replace("<HEAD>", f"<HEAD><base href=\"{url}\">")
            return text
        return Response(content, mimetype=content_type)
    except Exception as e:
        return str(e), 502

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
