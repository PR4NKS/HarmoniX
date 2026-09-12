"""Asynchronous database connection and migration engine for SQLite."""

import aiosqlite
import asyncio
from pathlib import Path
from typing import Optional
from utils.logging import get_logger

logger = get_logger(__name__)

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    prefix TEXT NOT NULL DEFAULT '!',
    dj_role_id INTEGER DEFAULT NULL,
    music_channel_id INTEGER DEFAULT NULL,
    announce_channel_id INTEGER DEFAULT NULL,
    auto_leave BOOLEAN NOT NULL DEFAULT 1,
    default_volume INTEGER NOT NULL DEFAULT 80,
    max_queue INTEGER NOT NULL DEFAULT 500,
    language TEXT NOT NULL DEFAULT 'en',
    mode_247 BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    play_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    uri TEXT NOT NULL,
    author TEXT NOT NULL,
    duration INTEGER NOT NULL DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, uri)
);

CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    uri TEXT NOT NULL,
    author TEXT NOT NULL,
    duration INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL,
    FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS playback_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    uri TEXT NOT NULL,
    author TEXT NOT NULL,
    duration INTEGER NOT NULL DEFAULT 0,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS premium_subscriptions (
    guild_id INTEGER PRIMARY KEY,
    tier TEXT NOT NULL DEFAULT 'free',
    expires_at TIMESTAMP DEFAULT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS saved_queues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    queue_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, name)
);

CREATE INDEX IF NOT EXISTS idx_history_guild ON playback_history(guild_id);
CREATE INDEX IF NOT EXISTS idx_history_user ON playback_history(user_id);
CREATE INDEX IF NOT EXISTS idx_fav_user ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_pl_user ON playlists(user_id);
CREATE INDEX IF NOT EXISTS idx_plt_playlist ON playlist_tracks(playlist_id);
"""


class DatabaseManager:
    """Manages asynchronous SQLite connections and queries."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish connection and apply schema migrations."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row

        # Execute table schema migrations
        async with self._lock:
            await self._db.executescript(SCHEMA_SQL)
            await self._db.commit()

        logger.info("Database initialized and schema verified at %s", self.db_path)

    async def close(self) -> None:
        """Close active database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("Database connection closed.")

    @property
    def connection(self) -> aiosqlite.Connection:
        """Get underlying active connection."""
        if not self._db:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._db
