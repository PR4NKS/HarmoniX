"""Validation utilities for URLs, time stamps, duration formatting, and progress bars."""

import re
from typing import Optional
from urllib.parse import urlparse


URL_REGEX = re.compile(
    r"^(?:http|ftp)s?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})",
    re.IGNORECASE,
)

SPOTIFY_REGEX = re.compile(
    r"^(https?://)?(open\.spotify\.com)/(track|playlist|album|artist)/([a-zA-Z0-9]+)",
    re.IGNORECASE,
)

SOUNDCLOUD_REGEX = re.compile(
    r"^(https?://)?(www\.)?(soundcloud\.com)/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)",
    re.IGNORECASE,
)

APPLE_MUSIC_REGEX = re.compile(
    r"^(https?://)?(music\.apple\.com)/([a-z]{2})/(album|playlist|song)/",
    re.IGNORECASE,
)


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL."""
    return bool(URL_REGEX.match(url.strip()))


def is_youtube_url(url: str) -> bool:
    """Check if a URL points to YouTube."""
    return bool(YOUTUBE_REGEX.match(url.strip()))


def is_spotify_url(url: str) -> bool:
    """Check if a URL points to Spotify."""
    return bool(SPOTIFY_REGEX.match(url.strip()))


def is_soundcloud_url(url: str) -> bool:
    """Check if a URL points to SoundCloud."""
    return bool(SOUNDCLOUD_REGEX.match(url.strip()))


def is_apple_music_url(url: str) -> bool:
    """Check if a URL points to Apple Music."""
    return bool(APPLE_MUSIC_REGEX.match(url.strip()))


def format_duration(milliseconds: int) -> str:
    """Format duration in milliseconds into a readable [HH:]MM:SS string."""
    if milliseconds <= 0:
        return "00:00"

    # Lavalink streams with unbounded duration often have values > 24 hours or max int
    if milliseconds > 86400000 * 2:  # > 48 hours is effectively a live stream
        return "🔴 LIVE"

    seconds = int(milliseconds // 1000)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_time_to_seconds(time_str: str) -> Optional[int]:
    """Parse time string formats into seconds.
    Supported formats:
      - '120' -> 120s
      - '1:30' -> 90s
      - '01:30:00' -> 5400s
      - '2m' -> 120s
      - '1h30m' -> 5400s
    """
    time_str = time_str.strip().lower()

    # Plain seconds
    if time_str.isdigit():
        return int(time_str)

    # Colon format (HH:MM:SS or MM:SS)
    if ":" in time_str:
        parts = time_str.split(":")
        try:
            if len(parts) == 2:
                mins, secs = int(parts[0]), int(parts[1])
                return mins * 60 + secs
            elif len(parts) == 3:
                hours, mins, secs = int(parts[0]), int(parts[1]), int(parts[2])
                return hours * 3600 + mins * 60 + secs
        except ValueError:
            return None

    # Text format: e.g. 1h 2m 30s
    time_units = {"h": 3600, "m": 60, "s": 1}
    pattern = re.compile(r"(\d+)\s*([hms])")
    matches = pattern.findall(time_str)
    if matches:
        total_seconds = 0
        for amount, unit in matches:
            total_seconds += int(amount) * time_units[unit]
        return total_seconds

    return None


def create_progress_bar(current_ms: int, total_ms: int, length: int = 15) -> str:
    """Generate a modern text-based progress bar.
    Example: 🔘▬▬▬▬▬▬▬▬▬▬▬▬▬▬
             ▬▬▬🔘▬▬▬▬▬▬▬▬▬▬
    """
    if total_ms <= 0 or current_ms <= 0:
        return "🔘" + "▬" * (length - 1)

    if current_ms >= total_ms:
        return "▬" * (length - 1) + "🔘"

    ratio = min(max(current_ms / total_ms, 0.0), 1.0)
    pos = int(ratio * length)
    pos = min(pos, length - 1)

    bar = ["▬"] * length
    bar[pos] = "🔘"
    return "".join(bar)


def sanitize_text(text: str, max_length: int = 100) -> str:
    """Sanitize and truncate text to prevent embed overflow or injection."""
    clean = re.sub(r"[`*_~|]", "", text.strip())
    if len(clean) > max_length:
        return clean[: max_length - 3] + "..."
    return clean
