FROM python:3.12-slim

# FFmpeg is required by yt-dlp to merge video+audio and convert MP3/M4A
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -U yt-dlp

COPY server.py index.html ./

# Render / Railway / most hosts set $PORT; server.py reads it (default 8000)
CMD ["python", "server.py"]






