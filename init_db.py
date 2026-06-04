import os
import database as db

BASE = os.path.dirname(__file__)
conn = db.connect()
db.init_tables(conn)
db.seed_urls(conn, os.path.join(BASE, "urls.txt"))
conn.close()

stats = db.get_stats(db.connect())
print(f"Database: {stats['total']} URLs ({stats['pending']} pending, {stats['reviewed']} rated)")
