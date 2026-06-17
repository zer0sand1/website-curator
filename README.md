# Website Curator

Browse and curate a collection of personal websites. Swipe through hand-picked sites inside an embedded iframe, like the ones that catch your eye, and export your favorites.

Built with Flask (Python) and SQLite/PostgreSQL. Deployed on Render.

**Live site:** [https://website-curator-1.onrender.com](https://website-curator-1.onrender.com)

## Features

- **Curate** — Load one site at a time inside a proxied iframe. Navigate with in-site Back/Forward/Home buttons.
- **Like / Dislike** — Mark sites you like (♥) or skip with (✕). Add a note to remember why a site stood out.
- **Per-device liked sites** — Your liked sites are stored in your browser's localStorage, not on the server. Each device/browser has its own private collection that persists across refreshes.
- **Download as Markdown** — Export your liked sites as a `.md` file with names, links, and notes.
- **Mobile preview** — Open any site in a mobile-sized popup window.
- **History navigation** — Go back to previously curated sites with Prev/Next buttons.
- **Proxy** — Sites are loaded through a server-side proxy to bypass CORS and embedding restrictions.

## How it works

1. URLs are seeded from `urls.txt` into a database with a randomized sort order.
2. The curation page loads each site via a `/proxy` endpoint that fetches the page server-side and injects a `<base>` tag so relative links work inside the iframe.
3. Clicking **Like** stores the site in your browser's `localStorage` and advances to the next pending site.
4. The **Liked Sites** page reads your collection from `localStorage` — no login, no server-side storage of likes.
5. The **Download as Markdown** button generates a file like this:

```markdown
# Liked Websites

_Exported on June 17, 2026_

1. [example.com](https://example.com) — Great typography and color palette
2. [another.site](https://another.site)
```

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask, Gunicorn |
| Database | SQLite (dev) / PostgreSQL (production) |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Deployment | Render (Web Service + PostgreSQL) |

## Local development

```bash
# Clone the repo
git clone https://github.com/zer0sand1/website-curator.git
cd website-curator

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

The app starts at `http://localhost:8080`. It uses a local SQLite database (`curator.db`) by default. To use PostgreSQL, set the `DATABASE_URL` environment variable.

## Deployment

The project includes a `render.yaml` blueprint for one-click deploy on Render:

1. Fork or push to your GitHub repo.
2. On [render.com](https://render.com), create a new **Blueprint** and connect your repo.
3. Render provisions a web service and a PostgreSQL database automatically.
4. Deploys on every push to `main`.

## Project structure

```
├── app.py          # Flask routes and proxy
├── database.py     # SQLite/PostgreSQL abstraction layer
├── requirements.txt
├── Procfile
├── render.yaml
├── urls.txt        # Seed URLs
├── templates/
│   ├── index.html  # Curation page
│   └── liked.html  # Liked sites page
└── static/
    └── style.css
```
