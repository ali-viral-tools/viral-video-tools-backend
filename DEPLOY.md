# YouTube Downloader Tool — Backend Deploy Guide

Your front-end (`downloader-tool.txt` in your Artifacts tab) now has a working
backend in this folder. Together they make real downloads work.

## Files in this folder

| File | What it is |
|---|---|
| `index.html` | Your front-end, with the demo block replaced by a real call to `/api/download`. (Your original `downloader-tool.txt` is untouched.) |
| `server.py` | Python backend. Serves `index.html` and implements `POST /api/download` using yt-dlp + FFmpeg. |
| `requirements.txt` | Python dependencies: `flask`, `yt-dlp`. |

## How it works

1. Visitor pastes a YouTube link and picks a format (MP4 1080p → 144p, MP3 320/128, M4A).
2. The page sends `{ videoId, format }` to `POST /api/download`.
3. The server downloads + converts the video with yt-dlp and returns
   `{ "downloadUrl": "/dl/<token>/<file>" }`.
4. The browser starts the file download automatically. Files are deleted
   from the server after 30 minutes.

## Run it locally (test)

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python server.py
# open http://localhost:8000
```

















## Put it on hosting

Any host that runs Python with outbound internet works — Render, Railway,
Fly.io, Koyeb, or a VPS. (Avoid PythonAnywhere's free tier: it only allows
a whitelist of sites, and YouTube isn't on it, so downloads would fail.)

```bash
# on the server
pip install -r requirements.txt
python server.py          # or: gunicorn -b 0.0.0.0:8000 server:app
```

- Make sure **FFmpeg** is installed on the host (`ffmpeg -version`).
  Needed for merging video+audio and for MP3/M4A conversion.
- Open port `8000` (or set the `PORT` env var, e.g. `PORT=80 python server.py`).
- Point your domain at the server and you're live — page + API are one app.

### Option A — Render (recommended, ~15 minutes, free tier works)

1. Push the `backend/` folder to a GitHub repo as the repo root, so
   `Dockerfile`, `server.py`, `requirements.txt` and `index.html` sit at the
   top level. (The Dockerfile already installs FFmpeg; Render sets `$PORT`
   automatically and `server.py` reads it.)
2. Sign in at render.com → **New +** → **Web Service** → connect the repo.
   Render auto-detects the Dockerfile — leave build/start settings as-is.
3. **Plan:** Free. **Region:** the closest one (e.g. Singapore).
4. Deploy. When it's live you'll get a URL like
   `https://viral-video-tools-xxxx.onrender.com`.
5. Open `https://<your-url>/healthz` — you should see `{"ok":true}`.

> Free-tier note: Render sleeps the service after ~15 min of no traffic, so
> the first download of the day takes ~30–60s to wake up. The $7/mo plan
> keeps it always-on. For an always-on budget option, see Option B.






















### Option B — VPS (cheapest always-on)

A $4/mo Contabo / Hetzner / Hostinger VPS is always-on, so no cold starts.

```bash
sudo apt update && sudo apt install -y python3-venv ffmpeg nginx certbot python3-certbot-nginx
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Put Nginx in front as a reverse proxy to `localhost:8000` and use Certbot
for HTTPS (`certbot --nginx`).

## Front-end publishing (Blogger)

1. Copy the whole of `index.html`.
2. In Blogger → your site → **Pages** → **YouTube Video Downloader** →
   **Edit** → switch to **HTML view** → paste the whole file → **Save**.
3. On that Blogger page, replace the API base if you split the backend off
   somewhere else (the page currently calls `/api/download` on the same
   origin — that works as-is when the page is served by `server.py`).
   If your page lives on Blogger and your API lives on Render, change
   `fetch("/api/download", …)` to `fetch("https://<your-url>/api/download", …)`.
4. Ad slots: paste your ad network code into the two `<!-- AD SLOT: TOP -->`
   and `<!-- AD SLOT: BOTTOM -->` slots (currently empty). They are at
   `#ad-top` and `#ad-bottom` in `index.html`.

### Blogger page

The tool page is: https://viral-video-tools.blogspot.com/p/youtube-video-downloader.html

## Health check

```
GET https://<your-url>/healthz
=> {"ok":true}
```

## Notes

- Do not allow arbitrary file uploads — the API only downloads YouTube
  videos, and the download endpoint only serves files from its own job
  directory.
- If a download fails with a yt-dlp error, update yt-dlp on the server
  (`pip install -U yt-dlp`) — YouTube changes often break old versions.

## Tested

- Backend: `server.py` serves `index.html` and implements `/api/download`
  and `/dl/<token>/<name>`.
- Health endpoint: `/healthz` returns `{"ok":true}`.
- Date: 2026-10-24.
























