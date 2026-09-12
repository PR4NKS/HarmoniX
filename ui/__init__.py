"""UI components package."""

from .embeds import (
    create_now_playing_embed,
    create_track_queued_embed,
    create_playlist_queued_embed,
    create_queue_embed,
    create_success_embed,
    create_error_embed,
    create_info_embed,
    create_lyrics_embed,
)
from .views import (
    PlayerControlView,
    QueuePaginationView,
    SearchSelectView,
    LyricsPaginationView,
    disable_view_components,
)
from .modals import VolumeModal, SeekModal, PlaylistCreateModal

__all__ = [
    "create_now_playing_embed",
    "create_track_queued_embed",
    "create_playlist_queued_embed",
    "create_queue_embed",
    "create_success_embed",
    "create_error_embed",
    "create_info_embed",
    "create_lyrics_embed",
    "PlayerControlView",
    "QueuePaginationView",
    "SearchSelectView",
    "LyricsPaginationView",
    "disable_view_components",
    "VolumeModal",
    "SeekModal",
    "PlaylistCreateModal",
]
