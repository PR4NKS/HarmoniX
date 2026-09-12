"""Application settings and configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the Discord Music Bot."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Bot Identity & Discord Credentials
    DISCORD_TOKEN: str = Field(
        default="",
        description="The bot token from the Discord Developer Portal."
    )
    DEFAULT_PREFIX: str = Field(
        default="!",
        description="Fallback prefix for text commands."
    )
    BOT_NAME: str = Field(
        default="HarmoniX",
        description="Display name and brand of the music bot."
    )
    BOT_ACTIVITY: str = Field(
        default="🎵 /play | High-Fidelity Audio",
        description="Status activity string displayed by the bot."
    )

    # Lavalink Node Configuration
    LAVALINK_URI: str = Field(
        default="http://127.0.0.1:2333",
        description="Lavalink v4 REST/WebSocket URI (e.g. http://127.0.0.1:2333)."
    )
    LAVALINK_PASSWORD: str = Field(
        default="youshallnotpass",
        description="Password configured in Lavalink application.yml."
    )
    LAVALINK_INACTIVE_TIMEOUT: int = Field(
        default=60,
        description="Inactivity timeout before node reconnect retry."
    )

    # Spotify API Integration (Optional but recommended for rich metadata)
    SPOTIFY_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="Spotify Developer Application Client ID."
    )
    SPOTIFY_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="Spotify Developer Application Client Secret."
    )

    # Genius Lyrics API (Optional for lyrics service)
    GENIUS_API_TOKEN: Optional[str] = Field(
        default=None,
        description="Genius API Client Access Token."
    )

    # Database & Storage
    DATABASE_PATH: str = Field(
        default="data/bot_database.sqlite3",
        description="SQLite database file path."
    )

    # Playback & Queue Defaults
    DEFAULT_VOLUME: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Default playback volume (0-100)."
    )
    MAX_QUEUE_SIZE: int = Field(
        default=500,
        ge=10,
        le=5000,
        description="Maximum tracks permitted in a guild queue."
    )
    MAX_PLAYLIST_SIZE: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum tracks importable from a single playlist."
    )
    DEFAULT_SEARCH_SOURCE: str = Field(
        default="ytmsearch",
        description="Default search prefix (e.g. ytmsearch, scsearch, ytsearch)."
    )
    AUTO_LEAVE_SECONDS: int = Field(
        default=180,
        description="Seconds to wait before disconnecting when alone or idle in VC."
    )

    # Visual Theme & Embed Styling
    COLOR_PRIMARY: int = Field(
        default=0x5865F2,
        description="Brand primary color (Discord Blurple)."
    )
    COLOR_SUCCESS: int = Field(
        default=0x2ECC71,
        description="Success embed color."
    )
    COLOR_WARNING: int = Field(
        default=0xF1C40F,
        description="Warning embed color."
    )
    COLOR_ERROR: int = Field(
        default=0xE74C3C,
        description="Error embed color."
    )
    COLOR_SECONDARY: int = Field(
        default=0x2B2D31,
        description="Dark background color for neutral states."
    )

    # Logging & Debug
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL."
    )
    LOG_FILE: str = Field(
        default="logs/bot.log",
        description="Path to log file output."
    )


@lru_cache()
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
