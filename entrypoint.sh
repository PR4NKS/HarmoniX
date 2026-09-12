#!/bin/bash
set -eo pipefail

echo "=========================================================="
echo "    HarmoniX Discord Music Bot - Railway Launchpad       "
echo "=========================================================="

mkdir -p /app/data /app/logs /app/plugins

# Setup Java memory allocation (default 512M suitable for 1GB containers)
JAVA_OPTS=${JAVA_OPTS:-"-Xmx512M -XX:+UseG1GC"}

# If Railway provides a PORT environment variable, run an optional lightweight HTTP health endpoint
HEALTH_PID=""
if [ -n "$PORT" ]; then
    echo "Railway PORT=$PORT detected. Starting lightweight HTTP health responder..."
    python -c "
import http.server, socketserver, os
port = int(os.environ.get('PORT', 8080))
class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'HarmoniX Bot is healthy and online.\n')
    def log_message(self, format, *args):
        pass
with socketserver.TCPServer(('', port), HealthHandler) as httpd:
    httpd.serve_forever()
" &
    HEALTH_PID=$!
fi

echo "[1/2] Starting Lavalink v4 Audio Server..."
java $JAVA_OPTS -jar /app/Lavalink.jar &
LAVALINK_PID=$!

echo "Waiting for Lavalink to be ready on port 2333..."
MAX_WAIT=60
WAITED=0
while ! curl -s -f http://127.0.0.1:2333/version > /dev/null 2>&1; do
    sleep 1
    WAITED=$((WAITED + 1))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "[ERROR] Lavalink failed to respond on port 2333 after $MAX_WAIT seconds."
        kill $LAVALINK_PID 2>/dev/null || true
        [ -n "$HEALTH_PID" ] && kill $HEALTH_PID 2>/dev/null || true
        exit 1
    fi
done

LAVALINK_VER=$(curl -s http://127.0.0.1:2333/version)
echo "[SUCCESS] Lavalink v4 is ready! (Version: $LAVALINK_VER)"

echo "[2/2] Starting HarmoniX Discord Bot..."
python main.py &
BOT_PID=$!

# Graceful termination handler
cleanup() {
    echo "Shutting down HarmoniX and Lavalink..."
    kill -TERM "$BOT_PID" 2>/dev/null || true
    kill -TERM "$LAVALINK_PID" 2>/dev/null || true
    [ -n "$HEALTH_PID" ] && kill -TERM "$HEALTH_PID" 2>/dev/null || true
    wait "$BOT_PID" 2>/dev/null || true
    wait "$LAVALINK_PID" 2>/dev/null || true
    [ -n "$HEALTH_PID" ] && wait "$HEALTH_PID" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for any process to exit
wait -n "$BOT_PID" "$LAVALINK_PID"
EXIT_CODE=$?

echo "A process exited with code $EXIT_CODE. Initiating cleanup..."
cleanup
