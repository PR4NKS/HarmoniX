"""Data models for database records."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class GuildSettingsModel:
    guild_id: int
    prefix: str = "!"
    dj_role_id: Optional[int] = None
    music_channel_id: Optional[int] = None
    announce_channel_id: Optional[int] = None
    auto_leave: bool = True
    default_volume: int = 80
    max_queue: int = 500
    language: str = "en"
    mode_247: bool = False


@dataclass
class UserModel:
    user_id: int
    last_seen: datetime = field(default_factory=datetime.utcnow)
    play_count: int = 0


@dataclass
class FavoriteTrackModel:
    id: Optional[int] = None
    user_id: int = 0
    title: str = ""
    uri: str = ""
    author: str = ""
    duration: int = 0
    added_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PlaylistModel:
    id: Optional[int] = None
    user_id: int = 0
    name: str = ""
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    tracks: List["PlaylistTrackModel"] = field(default_factory=list)


@dataclass
class PlaylistTrackModel:
    id: Optional[int] = None
    playlist_id: int = 0
    title: str = ""
    uri: str = ""
    author: str = ""
    duration: int = 0
    position: int = 0


@dataclass
class HistoryEntryModel:
    id: Optional[int] = None
    guild_id: int = 0
    user_id: int = 0
    title: str = ""
    uri: str = ""
    author: str = ""
    duration: int = 0
    played_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PremiumSubscriptionModel:
    guild_id: int
    tier: str = "free"
    expires_at: Optional[datetime] = None
    is_active: bool = False


@dataclass
class SavedQueueModel:
    id: Optional[int] = None
    guild_id: int = 0
    name: str = ""
    queue_data: str = "[]"
    created_at: datetime = field(default_factory=datetime.utcnow)
