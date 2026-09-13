# ==============================================================================
# HarmoniX Discord Music Bot - Production Dockerfile (Railway / Cloud Ready)
# Native Ubuntu 22.04 LTS + OpenJDK 21 LTS + Python 3 + FFmpeg + Lavalink v4
# ==============================================================================

FROM eclipse-temurin:21-jre-jammy

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LAVALINK_URI="http://127.0.0.1:2333" \
    LAVALINK_PASSWORD="youshallnotpass" \
    STREAM_PROXY_HOST="127.0.0.1" \
    STREAM_PROXY_PORT=2334

# Install Python 3, pip, FFmpeg, curl, and build libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    python-is-python3 \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Download official Lavalink v4 executable directly from GitHub releases
RUN curl -fSL -o /app/Lavalink.jar https://github.com/lavalink-devs/Lavalink/releases/latest/download/Lavalink.jar

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete application source code and configuration
COPY . .

# Ensure storage directories exist, strip Windows CRLF line endings, and ensure executable permissions
RUN mkdir -p /app/data /app/logs /app/plugins \
    && sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Expose Lavalink (2333), internal Stream Proxy (2334), and optional Web/Health (8080)
EXPOSE 2333 2334 8080

# Start entrypoint script via CMD (standard for Railway / Docker cloud runners)
CMD ["/app/entrypoint.sh"]
