#!/bin/bash
set -e

# Change directory to the root of the project
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "    HarmoniX Discord Music Bot - Production Launchpad     "
echo "=========================================================="

# 1. Check for DISCORD_TOKEN
if [ -z "$DISCORD_TOKEN" ] || [ "$DISCORD_TOKEN" = "your_discord_bot_token_here" ]; then
    echo ""
    echo "=========================================================="
    echo "[CRITICAL ERROR] DISCORD_TOKEN is missing or not configured!"
    echo "=========================================================="
    echo "How to fix:"
    echo "1. Set DISCORD_TOKEN in your .env file or environment variables."
    echo "2. If deploying to Railway/Render/Fly.io, add DISCORD_TOKEN"
    echo "   under the service Variables settings."
    echo "=========================================================="
    echo ""
    exit 1
fi

mkdir -p data logs plugins

# Check if external Lavalink URI is configured
START_INTERNAL_LAVALINK=true
if [ -n "$LAVALINK_URI" ] && [[ "$LAVALINK_URI" != *"127.0.0.1"* ]] && [[ "$LAVALINK_URI" != *"localhost"* ]]; then
    START_INTERNAL_LAVALINK=false
    echo "External Lavalink URI detected ($LAVALINK_URI). Skipping internal Lavalink startup."
fi

LAVALINK_PID=""
if [ "$START_INTERNAL_LAVALINK" = true ]; then
    # 2. Check for Lavalink.jar
    if [ ! -f "Lavalink.jar" ]; then
        echo "Downloading Lavalink v4 directly..."
        curl -fSL -o Lavalink.jar https://github.com/lavalink-devs/Lavalink/releases/latest/download/Lavalink.jar
    fi

    # 3. Setup Java memory
    JAVA_OPTS=${JAVA_OPTS:-"-Xmx512M -XX:+UseG1GC"}
    JAVA_CMD="java"
    if [ -n "$JAVA_HOME" ] && [ -x "$JAVA_HOME/bin/java" ]; then
        JAVA_CMD="$JAVA_HOME/bin/java"
    fi

    LAVALINK_PASS="${LAVALINK_PASSWORD:-youshallnotpass}"

    # 4. Start Lavalink audio server in background
    echo "[1/2] Starting Lavalink v4 Audio Server..."
    $JAVA_CMD $JAVA_OPTS -jar Lavalink.jar &
    LAVALINK_PID=$!

    # Wait for Lavalink port 2333 with Authorization header (up to 30 seconds)
    echo "Waiting for Lavalink to initialize on port 2333..."
    for i in {1..30}; do
        if curl -s -f -H "Authorization: $LAVALINK_PASS" http://127.0.0.1:2333/version > /dev/null 2>&1; then
            LAVALINK_VER=$(curl -s -H "Authorization: $LAVALINK_PASS" http://127.0.0.1:2333/version)
            echo "[SUCCESS] Lavalink v4 is ready! (Version: $LAVALINK_VER)"
            break
        fi
        sleep 1
    done
fi

# If cloud provider provides a PORT environment variable, run an optional lightweight HTTP health responder
HEALTH_PID=""
if [ -n "$PORT" ]; then
    echo "Cloud PORT=$PORT detected. Starting lightweight HTTP health responder..."
    python3 -c "
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

# 5. Start HarmoniX Python Bot
PYTHON_CMD="python3"
if ! command -v python3 > /dev/null 2>&1; then
    PYTHON_CMD="python"
fi

echo "[2/2] Starting HarmoniX Discord Bot (main.py)..."
$PYTHON_CMD main.py &
BOT_PID=$!

# Graceful termination handler
cleanup() {
    echo "Shutting down HarmoniX and background services..."
    [ -n "$BOT_PID" ] && kill -TERM "$BOT_PID" 2>/dev/null || true
    [ -n "$LAVALINK_PID" ] && kill -TERM "$LAVALINK_PID" 2>/dev/null || true
    [ -n "$HEALTH_PID" ] && kill -TERM "$HEALTH_PID" 2>/dev/null || true
    [ -n "$BOT_PID" ] && wait "$BOT_PID" 2>/dev/null || true
    [ -n "$LAVALINK_PID" ] && wait "$LAVALINK_PID" 2>/dev/null || true
    [ -n "$HEALTH_PID" ] && wait "$HEALTH_PID" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep the container alive while the bot is running
wait "$BOT_PID"
EXIT_CODE=$?

echo "HarmoniX bot process exited with code $EXIT_CODE. Cleaning up..."
cleanup
