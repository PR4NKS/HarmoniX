"""Database module."""

from .connection import DatabaseManager
from .repository import MusicRepository
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

__all__ = [
    "DatabaseManager",
    "MusicRepository",
    "GuildSettingsModel",
    "UserModel",
    "FavoriteTrackModel",
    "PlaylistModel",
    "PlaylistTrackModel",
    "HistoryEntryModel",
    "PremiumSubscriptionModel",
    "SavedQueueModel",
]
