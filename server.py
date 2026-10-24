#!/usr/bin/env python3
"""
YouTube Downloader Tool - backend server.

Serves the single-page front-end (index.html) and implements the
BACKEND INTEGRATION POINT the front-end expects:

    POST /api/download   { "videoId": "dQw4w9WgXcQ", "format": "mp4-720" }
      -> 200 { "downloadUrl": "/dl/<token>" }
      -> 400 { "error": "..." } on bad input / failed download

    GET /dl/<token>      -> the finished file as an attachment

Run:
    pip install -r requirements.txt
    python server.py
Then open http://localhost:8000

Deploy notes are in DEPLOY.md.
"""
import os
import re
import secrets
import shutil
import threading
import time
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file
from flask_cors import CORS

BASE = Path(__file__).resolve().parent
DL_DIR = BASE / "downloads"
DL_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=None)  # no catch-all static route

# The Blogger tool page lives on *.blogspot.com and calls this API
# cross-origin, so the API (and only the API) allows CORS.
CORS(app, resources={r"/api/*": {"origins": "*"}})

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")























# Maps the front-end dropdown values to yt-dlp format selectors.
# "audio": (codec, quality) -> convert with FFmpeg after download.
FORMATS = {
    "mp4-1080": {"ydl": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best", "audio": None, "ext": "mp4"},
    "mp4-720":  {"ydl": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",  "audio": None, "ext": "mp4"},
    "mp4-480":  {"ydl": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",  "audio": None, "ext": "mp4"},
    "mp4-360":  {"ydl": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]/best",  "audio": None, "ext": "mp4"},
    "mp4-144":  {"ydl": "bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=144]+bestaudio/best[height<=144]/best",  "audio": None, "ext": "mp4"},
    "mp3-320":  {"ydl": "bestaudio/best", "audio": ("mp3", "320K"), "ext": "mp3"},
    "mp3-128":  {"ydl": "bestaudio/best", "audio": ("mp3", "128K"), "ext": "mp3"},
    "m4a":      {"ydl": "bestaudio/best", "audio": ("m4a", None),   "ext": "m4a"},
}













# Files are kept for this long so the browser has time to start the download.
FILE_TTL_SECONDS = 30 * 60


def _cleanup_loop():
    while True:
        now = time.time()
        for job_dir in DL_DIR.iterdir():
            try:
                if job_dir.is_dir() and now - job_dir.stat().st_mtime > FILE_TTL_SECONDS:
                    shutil.rmtree(job_dir, ignore_errors=True)
            except OSError:
                pass
        time.sleep(10 * 60)


threading.Thread(target=_cleanup_loop, daemon=True).start()


@app.get("/")
def index():
    page = BASE / "index.html"
    if not page.exists():
        abort(404, description="index.html missing - copy downloader-tool.txt to index.html")
    return send_file(page, mimetype="text/html")


@app.get("/healthz")
def healthz():
    return jsonify(ok=True)



















@app.post("/api/download")
def api_download():
    data = request.get_json(silent=True) or {}
    video_id = str(data.get("videoId", "")).strip()
    fmt_key = str(data.get("format", "")).strip()

    if not VIDEO_ID_RE.match(video_id):
        return jsonify(error="Invalid video ID."), 400
    spec = FORMATS.get(fmt_key)
    if not spec:
        return jsonify(error="Unknown format."), 400

    token = secrets.token_urlsafe(16)
    job_dir = DL_DIR / token
    job_dir.mkdir(parents=True)

    try:
        from yt_dlp import YoutubeDL

        ydl_opts = {
            "format": spec["ydl"],
            "outtmpl": str(job_dir / "%(title).80s.%(ext)s"),














            "merge_output_format": "mp4" if spec["ext"] == "mp4" else None,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
                        "extractor_args": {
                            "youtube": {
                                "player_client": [
                                    "ios",
                                    "android",
                                    "tv_embedded",
                                    "web_embedded",
                                    "web",
                                ],
                            }
                        },
            "postprocessors": [],
        }
        if spec["ext"] == "mp4":
            ydl_opts["postprocessors"].append(
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
            )
        elif spec["audio"]:
            codec, quality = spec["audio"]
            pp = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
            if quality:
                pp["preferredquality"] = quality.replace("K", "")
            ydl_opts["postprocessors"].append(pp)

        url = "https://www.youtube.com/watch?v=" + video_id
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])





















        files = [p for p in job_dir.iterdir() if p.is_file()]
        if not files:
            raise RuntimeError("Download produced no file.")
        if len(files) > 1:
            # Prefer the fully-converted output over intermediate parts.
            files.sort(key=lambda p: (p.suffix == f".{spec['ext']}", p.stat().st_size))
        final = files[-1]
        return jsonify(downloadUrl=f"/dl/{token}/{final.name}")

    except Exception as exc:  # noqa: BLE001 - surface a clean message to the UI
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify(error=f"Download failed: {exc}"), 502


@app.get("/dl/<token>/<name>")
def serve_file(token, name):
    # Keep the file strictly inside its own job directory.
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", token):
        abort(404)
    path = (DL_DIR / token / Path(name).name).resolve()
    if DL_DIR not in path.parents or not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))



















