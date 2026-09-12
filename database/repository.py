"""Database repository with typed asynchronous CRUD operations."""

import json
from typing import Optional, List, Dict, Any
from .connection import DatabaseManager
from .models import (
    GuildSettingsModel,
    UserModel,
    FavoriteTrackModel,
    PlaylistModel,
    PlaylistTrackModel,
    HistoryEntryModel,
    PremiumSubscriptionModel,
    SavedQueueModel,
)
from utils.logging import get_logger

logger = get_logger(__name__)


class MusicRepository:
    """Encapsulates all database operations for HarmoniX."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    # -------------------------------------------------------------
    # Guild Settings
    # -------------------------------------------------------------
    async def get_guild_settings(self, guild_id: int) -> GuildSettingsModel:
        """Fetch settings for a guild, inserting defaults if not present."""
        query = "SELECT * FROM guild_settings WHERE guild_id = ?"
        async with self.db.connection.execute(query, (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return GuildSettingsModel(
                    guild_id=row["guild_id"],
                    prefix=row["prefix"],
                    dj_role_id=row["dj_role_id"],
                    music_channel_id=row["music_channel_id"],
                    announce_channel_id=row["announce_channel_id"],
                    auto_leave=bool(row["auto_leave"]),
                    default_volume=row["default_volume"],
                    max_queue=row["max_queue"],
                    language=row["language"],
                    mode_247=bool(row["mode_247"]),
                )

        # Create default
        default_model = GuildSettingsModel(guild_id=guild_id)
        insert_query = """
            INSERT INTO guild_settings (guild_id, prefix, default_volume, max_queue, auto_leave, mode_247)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        await self.db.connection.execute(
            insert_query,
            (
                guild_id,
                default_model.prefix,
                default_model.default_volume,
                default_model.max_queue,
                default_model.auto_leave,
                default_model.mode_247,
            ),
        )
        await self.db.connection.commit()
        return default_model

    async def update_guild_settings(self, guild_id: int, **kwargs) -> GuildSettingsModel:
        """Update individual settings fields for a guild."""
        if not kwargs:
            return await self.get_guild_settings(guild_id)

        # Ensure record exists
        await self.get_guild_settings(guild_id)

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [guild_id]
        query = f"UPDATE guild_settings SET {set_clause} WHERE guild_id = ?"

        await self.db.connection.execute(query, values)
        await self.db.connection.commit()
        return await self.get_guild_settings(guild_id)

    async def reset_guild_settings(self, guild_id: int) -> GuildSettingsModel:
        """Reset guild settings to factory defaults."""
        await self.db.connection.execute("DELETE FROM guild_settings WHERE guild_id = ?", (guild_id,))
        await self.db.connection.commit()
        return await self.get_guild_settings(guild_id)

    # -------------------------------------------------------------
    # Playback History & Statistics
    # -------------------------------------------------------------
    async def record_playback(
        self,
        guild_id: int,
        user_id: int,
        title: str,
        uri: str,
        author: str,
        duration: int,
    ) -> None:
        """Log a track playback in history and bump user play count."""
        insert_hist = """
            INSERT INTO playback_history (guild_id, user_id, title, uri, author, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        await self.db.connection.execute(insert_hist, (guild_id, user_id, title, uri, author, duration))

        upsert_user = """
            INSERT INTO users (user_id, last_seen, play_count)
            VALUES (?, CURRENT_TIMESTAMP, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                last_seen = CURRENT_TIMESTAMP,
                play_count = play_count + 1
        """
        await self.db.connection.execute(upsert_user, (user_id,))
        await self.db.connection.commit()

    async def get_guild_history(self, guild_id: int, limit: int = 15) -> List[HistoryEntryModel]:
        """Fetch recently played tracks for a guild."""
        query = """
            SELECT * FROM playback_history
            WHERE guild_id = ?
            ORDER BY played_at DESC
            LIMIT ?
        """
        async with self.db.connection.execute(query, (guild_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [
                HistoryEntryModel(
                    id=row["id"],
                    guild_id=row["guild_id"],
                    user_id=row["user_id"],
                    title=row["title"],
                    uri=row["uri"],
                    author=row["author"],
                    duration=row["duration"],
                    played_at=row["played_at"],
                )
                for row in rows
            ]

    async def get_most_played(self, guild_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch most frequently played tracks."""
        if guild_id:
            query = """
                SELECT title, author, uri, COUNT(*) as play_count
                FROM playback_history
                WHERE guild_id = ?
                GROUP BY uri
                ORDER BY play_count DESC
                LIMIT ?
            """
            params = (guild_id, limit)
        else:
            query = """
                SELECT title, author, uri, COUNT(*) as play_count
                FROM playback_history
                GROUP BY uri
                ORDER BY play_count DESC
                LIMIT ?
            """
            params = (limit,)

        async with self.db.connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "title": row["title"],
                    "author": row["author"],
                    "uri": row["uri"],
                    "play_count": row["play_count"],
                }
                for row in rows
            ]

    # -------------------------------------------------------------
    # User Favorites
    # -------------------------------------------------------------
    async def add_favorite(
        self,
        user_id: int,
        title: str,
        uri: str,
        author: str,
        duration: int,
    ) -> bool:
        """Add a track to user's favorites list. Returns True if added, False if duplicate."""
        query = """
            INSERT INTO favorites (user_id, title, uri, author, duration)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, uri) DO NOTHING
        """
        cursor = await self.db.connection.execute(query, (user_id, title, uri, author, duration))
        await self.db.connection.commit()
        return cursor.rowcount > 0

    async def remove_favorite(self, user_id: int, uri_or_title: str) -> bool:
        """Remove a track from user's favorites."""
        query = """
            DELETE FROM favorites
            WHERE user_id = ? AND (uri = ? OR LOWER(title) = LOWER(?))
        """
        cursor = await self.db.connection.execute(query, (user_id, uri_or_title, uri_or_title))
        await self.db.connection.commit()
        return cursor.rowcount > 0

    async def get_favorites(self, user_id: int) -> List[FavoriteTrackModel]:
        """Fetch all favorites for a user."""
        query = "SELECT * FROM favorites WHERE user_id = ? ORDER BY added_at DESC"
        async with self.db.connection.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [
                FavoriteTrackModel(
                    id=row["id"],
                    user_id=row["user_id"],
                    title=row["title"],
                    uri=row["uri"],
                    author=row["author"],
                    duration=row["duration"],
                    added_at=row["added_at"],
                )
                for row in rows
            ]

    # -------------------------------------------------------------
    # Playlists
    # -------------------------------------------------------------
    async def create_playlist(self, user_id: int, name: str, is_public: bool = False) -> Optional[int]:
        """Create a new playlist. Returns playlist ID or None if name exists for user."""
        query = """
            INSERT INTO playlists (user_id, name, is_public)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, name) DO NOTHING
        """
        cursor = await self.db.connection.execute(query, (user_id, name.strip(), is_public))
        await self.db.connection.commit()
        return cursor.lastrowid if cursor.rowcount > 0 else None

    async def delete_playlist(self, user_id: int, name: str) -> bool:
        """Delete a user playlist by name."""
        query = "DELETE FROM playlists WHERE user_id = ? AND LOWER(name) = LOWER(?)"
        cursor = await self.db.connection.execute(query, (user_id, name.strip()))
        await self.db.connection.commit()
        return cursor.rowcount > 0

    async def get_user_playlists(self, user_id: int) -> List[PlaylistModel]:
        """Fetch all playlists owned by a user."""
        query = "SELECT * FROM playlists WHERE user_id = ? ORDER BY created_at DESC"
        async with self.db.connection.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [
                PlaylistModel(
                    id=row["id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    is_public=bool(row["is_public"]),
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    async def add_track_to_playlist(
        self,
        playlist_id: int,
        title: str,
        uri: str,
        author: str,
        duration: int,
    ) -> bool:
        """Append track to playlist."""
        # Get current maximum position
        pos_query = "SELECT COALESCE(MAX(position), 0) + 1 FROM playlist_tracks WHERE playlist_id = ?"
        async with self.db.connection.execute(pos_query, (playlist_id,)) as cursor:
            pos_row = await cursor.fetchone()
            position = pos_row[0] if pos_row else 1

        insert = """
            INSERT INTO playlist_tracks (playlist_id, title, uri, author, duration, position)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = await self.db.connection.execute(insert, (playlist_id, title, uri, author, duration, position))
        await self.db.connection.commit()
        return cursor.rowcount > 0

    async def get_playlist_tracks(self, playlist_id: int) -> List[PlaylistTrackModel]:
        """Fetch all tracks in a playlist ordered by position."""
        query = "SELECT * FROM playlist_tracks WHERE playlist_id = ? ORDER BY position ASC"
        async with self.db.connection.execute(query, (playlist_id,)) as cursor:
            rows = await cursor.fetchall()
            return [
                PlaylistTrackModel(
                    id=row["id"],
                    playlist_id=row["playlist_id"],
                    title=row["title"],
                    uri=row["uri"],
                    author=row["author"],
                    duration=row["duration"],
                    position=row["position"],
                )
                for row in rows
            ]

    async def get_playlist_by_name(self, user_id: int, name: str) -> Optional[PlaylistModel]:
        """Fetch a specific playlist owned by user or public."""
        query = """
            SELECT * FROM playlists
            WHERE (user_id = ? OR is_public = 1) AND LOWER(name) = LOWER(?)
            LIMIT 1
        """
        async with self.db.connection.execute(query, (user_id, name.strip())) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            pl = PlaylistModel(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                is_public=bool(row["is_public"]),
                created_at=row["created_at"],
            )
            pl.tracks = await self.get_playlist_tracks(pl.id)
            return pl

    # -------------------------------------------------------------
    # Saved Queues
    # -------------------------------------------------------------
    async def save_queue(self, guild_id: int, name: str, tracks_data: List[Dict[str, Any]]) -> bool:
        """Save a snapshot of the current guild queue."""
        data_str = json.dumps(tracks_data)
        query = """
            INSERT INTO saved_queues (guild_id, name, queue_data)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, name) DO UPDATE SET
                queue_data = excluded.queue_data,
                created_at = CURRENT_TIMESTAMP
        """
        cursor = await self.db.connection.execute(query, (guild_id, name.strip(), data_str))
        await self.db.connection.commit()
        return cursor.rowcount > 0

    async def load_saved_queue(self, guild_id: int, name: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve a saved queue's track data."""
        query = "SELECT queue_data FROM saved_queues WHERE guild_id = ? AND LOWER(name) = LOWER(?)"
        async with self.db.connection.execute(query, (guild_id, name.strip())) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row["queue_data"])
                except Exception:
                    return None
            return None

    async def list_saved_queues(self, guild_id: int) -> List[str]:
        """List all saved queue names for a guild."""
        query = "SELECT name FROM saved_queues WHERE guild_id = ? ORDER BY created_at DESC"
        async with self.db.connection.execute(query, (guild_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row["name"] for row in rows]

    async def delete_saved_queue(self, guild_id: int, name: str) -> bool:
        """Delete a saved queue."""
        query = "DELETE FROM saved_queues WHERE guild_id = ? AND LOWER(name) = LOWER(?)"
        cursor = await self.db.connection.execute(query, (guild_id, name.strip()))
        await self.db.connection.commit()
        return cursor.rowcount > 0

    # -------------------------------------------------------------
    # Premium Subscriptions
    # -------------------------------------------------------------
    async def get_premium_status(self, guild_id: int) -> PremiumSubscriptionModel:
        """Check premium subscription status for a guild."""
        query = "SELECT * FROM premium_subscriptions WHERE guild_id = ?"
        async with self.db.connection.execute(query, (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return PremiumSubscriptionModel(
                    guild_id=row["guild_id"],
                    tier=row["tier"],
                    expires_at=row["expires_at"],
                    is_active=bool(row["is_active"]),
                )
        return PremiumSubscriptionModel(guild_id=guild_id, tier="free", is_active=False)

    async def set_premium_status(self, guild_id: int, tier: str, is_active: bool) -> None:
        """Set premium status for a guild."""
        query = """
            INSERT INTO premium_subscriptions (guild_id, tier, is_active)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                tier = excluded.tier,
                is_active = excluded.is_active
        """
        await self.db.connection.execute(query, (guild_id, tier, is_active))
        await self.db.connection.commit()
