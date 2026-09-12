# ==============================================================================
# HarmoniX Discord Music Bot - Production Dockerfile (Railway / Cloud Ready)
# Unified Container: OpenJDK 21 LTS (Lavalink v4) + Python 3.11 (Discord Bot)
# ==============================================================================

# Stage 1: Extract Eclipse Temurin OpenJDK 21 JRE
FROM eclipse-temurin:21-jre-jammy AS jre-stage

# Stage 2: Final Production Environment
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    JAVA_HOME=/opt/java/openjdk \
    PATH="/opt/java/openjdk/bin:${PATH}" \
    LAVALINK_URI="http://127.0.0.1:2333" \
    LAVALINK_PASSWORD="youshallnotpass"

# Install FFmpeg, curl, and essential native libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    libffi-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy OpenJDK 21 from jre-stage
COPY --from=jre-stage /opt/java/openjdk /opt/java/openjdk

WORKDIR /app

# Download official Lavalink v4 executable directly from GitHub releases
RUN curl -fSL -o /app/Lavalink.jar https://github.com/lavalink-devs/Lavalink/releases/latest/download/Lavalink.jar

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete application source code and configuration
COPY . .

# Ensure storage directories exist, strip Windows CRLF line endings, and ensure executable permissions
RUN mkdir -p /app/data /app/logs /app/plugins \
    && sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Launch entrypoint managing Lavalink v4 and HarmoniX Discord Bot
ENTRYPOINT ["/app/entrypoint.sh"]
