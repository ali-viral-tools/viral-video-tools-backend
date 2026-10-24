#!/bin/sh
node bgutil-ytdlp-pot-provider/server/build/main.js --port 4416 --host 127.0.0.1 &
exec python server.py
