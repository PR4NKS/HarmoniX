#!/bin/bash
set -e

# Change directory to the root of the project
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "    HarmoniX Discord Music Bot - Railway Launchpad       "
echo "=========================================================="

# 1. Check for DISCORD_TOKEN
if [ -z "$DISCORD_TOKEN" ] || [ "$DISCORD_TOKEN" = "your_discord_bot_token_here" ]; then
    echo ""
    echo "=========================================================="
    echo "[CRITICAL ERROR] DISCORD_TOKEN is missing or not configured!"
    echo "=========================================================="
    echo "How to fix this in Railway:"
    echo "1. Open your Railway project dashboard: https://railway.com"
    echo "2. Click on your HarmoniX service."
    echo "3. Go to the 'Variables' tab."
    echo "4. Click '+ New Variable' and add:"
    echo "     Variable Name : DISCORD_TOKEN"
    echo "     Value         : (Your actual Discord bot token)"
    echo "5. Railway will automatically redeploy and start the bot!"
    echo "=========================================================="
    echo ""
    exit 1
fi

mkdir -p data logs plugins

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

# If Railway provides a PORT environment variable, run an optional lightweight HTTP health responder
HEALTH_PID=""
if [ -n "$PORT" ]; then
    echo "Railway PORT=$PORT detected. Starting lightweight HTTP health responder..."
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

# Keep the container alive while the bot is running
wait "$BOT_PID"
EXIT_CODE=$?

echo "HarmoniX bot process exited with code $EXIT_CODE. Cleaning up..."
cleanup
