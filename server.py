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
    "mp4-1080": {"ydl": "bestvideo+bestaudio/best", "audio": None, "ext": "mp4"},
    "mp4-720":  {"ydl": "bestvideo+bestaudio/best",  "audio": None, "ext": "mp4"},
    "mp4-480":  {"ydl": "bestvideo+bestaudio/best",  "audio": None, "ext": "mp4"},
    "mp4-360":  {"ydl": "bestvideo+bestaudio/best",  "audio": None, "ext": "mp4"},
    "mp4-144":  {"ydl": "bestvideo+bestaudio/best",  "audio": None, "ext": "mp4"},
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



















@app.get("/api/formats")
def api_formats():
    video_id = str(request.args.get("videoId", "")).strip()
    if not VIDEO_ID_RE.match(video_id):
        return jsonify(error="Invalid video ID."), 400
    try:
        from yt_dlp import YoutubeDL
        import yt_dlp
        import os as _os
        _cookie_path = _os.environ.get("YT_COOKIES_PATH", "/etc/secrets/cookies.txt")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "extractor_args": {
                "youtube": {},
            },
        }
        if _os.path.exists(_cookie_path):
            shutil.copyfile(_cookie_path, "/tmp/cookies.txt")
            ydl_opts["cookiefile"] = "/tmp/cookies.txt"
            cookie_file_exists = True
            cookie_names = []
            cookie_count = 0
            cookie_load_error = None
            try:
                import http.cookiejar
                _jar = http.cookiejar.MozillaCookieJar("/tmp/cookies.txt")
                _jar.load(ignore_discard=True, ignore_expires=True)
                cookie_names = [c.name for c in _jar]
                cookie_count = len(cookie_names)
            except Exception as _cookie_exc:
                cookie_load_error = str(_cookie_exc)
        else:
            cookie_file_exists = False
            cookie_names = []
            cookie_count = 0
            cookie_load_error = None
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/watch?v=" + video_id, download=False, process=False)
        fmts = [{"format_id": f.get("format_id"), "ext": f.get("ext"), "height": f.get("height"), "vcodec": f.get("vcodec"), "acodec": f.get("acodec")} for f in (info.get("formats") or [])]
        return jsonify(title=info.get("title"), yt_dlp_version=yt_dlp.version.__version__, format_count=len(fmts), formats=fmts[:60], cookie_file_exists=cookie_file_exists, cookie_names=cookie_names, **({"cookie_count": cookie_count} if cookie_load_error is None else {"cookie_load_error": cookie_load_error}))
    except Exception as exc:
        return jsonify(error=str(exc)), 500
@app.get("/api/diag")
def api_diag():
    video_id = str(request.args.get("videoId", "")).strip()
    if not VIDEO_ID_RE.match(video_id):
        return jsonify(error="Invalid video ID."), 400
    try:
        from yt_dlp import YoutubeDL
        import os as _os, io, logging
        _cookie_path = _os.environ.get("YT_COOKIES_PATH", "/etc/secrets/cookies.txt")
        _buf = io.StringIO()
        class _H(logging.Handler):
            def emit(self, record):
                _buf.write(self.format(record) + "\n")
        _h = _H()
        _h.setFormatter(logging.Formatter("%(message)s"))
        _logger = logging.getLogger("yt-dlp")
        _logger.addHandler(_h)
        _logger.setLevel(logging.DEBUG)
        ydl_opts = {"quiet": False, "verbose": True, "no_warnings": False, "socket_timeout": 30, "extractor_args": {"youtube": {}}, "logger": _logger}
        if _os.path.exists(_cookie_path):
            shutil.copyfile(_cookie_path, "/tmp/cookies.txt")
            ydl_opts["cookiefile"] = "/tmp/cookies.txt"
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/watch?v=" + video_id, download=False, process=False)
        _logger.removeHandler(_h)
        _log = _buf.getvalue()
        # Return only safe lines: playability, client, format, error, storyboard lines, last 80 lines total, with no cookie values. Strip any line containing "cookie" case-insensitively except a count line.
        _lines = [l for l in _log.splitlines() if "cookie" not in l.lower()]
        return jsonify(title=info.get("title"), playability=(info.get("playability") or {}), format_count=len(info.get("formats") or []), log_tail=_lines[-80:])
    except Exception as exc:
        return jsonify(error=str(exc)), 500
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

        import os as _os
        _cookie_path = _os.environ.get("YT_COOKIES_PATH", "/etc/secrets/cookies.txt")
        ydl_opts = {
            "format": spec["ydl"],
            "outtmpl": str(job_dir / "%(title).80s.%(ext)s"),














            "merge_output_format": "mp4" if spec["ext"] == "mp4" else None,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
                        "extractor_args": {
                "youtube": {},
                        },
            "postprocessors": [],
        }
        if _os.path.exists(_cookie_path):
            _tmp_cookies = "/tmp/cookies.txt"
            shutil.copyfile(_cookie_path, _tmp_cookies)
            ydl_opts["cookiefile"] = _tmp_cookies
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



















