"""SoundCloud source adapter."""

from typing import Optional, List, Union
import discord
import wavelink
from .base import BaseAudioSource, PlaylistResult
from music.track import HarmoniXTrack
from utils.validators import is_soundcloud_url


class SoundCloudSource(BaseAudioSource):
    """Adapter for resolving SoundCloud tracks and sets via Lavalink."""

    def __init__(self):
        super().__init__("soundcloud")

    def can_handle(self, query: str) -> bool:
        return is_soundcloud_url(query) or query.strip().startswith("scsearch:")

    async def resolve(
        self,
        query: str,
        requester: Optional[discord.Member] = None,
        max_results: int = 10,
    ) -> Union[List[HarmoniXTrack], PlaylistResult]:
        query_str = query.strip()
        results = await wavelink.Playable.search(query_str, source=wavelink.TrackSource.SoundCloud)
        if not results:
            return []

        if isinstance(results, wavelink.Playlist):
            playlist_name = getattr(results, "name", "SoundCloud Playlist")
            tracks = [
                HarmoniXTrack(
                    playable=track,
                    requester=requester,
                    source_name="soundcloud",
                )
                for track in results
            ]
            return PlaylistResult(name=playlist_name, tracks=tracks)

        return [
            HarmoniXTrack(
                playable=track,
                requester=requester,
                source_name="soundcloud",
            )
            for track in results[:max_results]
        ]
