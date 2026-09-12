"""Direct URL and internet radio stream adapter."""

from typing import Optional, List, Union
import discord
import wavelink
from .base import BaseAudioSource, PlaylistResult
from music.track import HarmoniXTrack
from utils.validators import is_valid_url, is_youtube_url, is_spotify_url, is_soundcloud_url, is_apple_music_url


class DirectURLSource(BaseAudioSource):
    """Adapter for resolving direct audio streams and web radio URLs."""

    def __init__(self):
        super().__init__("direct_url")

    def can_handle(self, query: str) -> bool:
        if not is_valid_url(query):
            return False
        # If it is not one of the major platforms, treat as direct URL / radio stream
        return not (
            is_youtube_url(query)
            or is_spotify_url(query)
            or is_soundcloud_url(query)
            or is_apple_music_url(query)
        )

    async def resolve(
        self,
        query: str,
        requester: Optional[discord.Member] = None,
        max_results: int = 1,
    ) -> Union[List[HarmoniXTrack], PlaylistResult]:
        results = await wavelink.Playable.search(query.strip())
        if not results:
            return []

        if isinstance(results, wavelink.Playlist):
            tracks = [
                HarmoniXTrack(
                    playable=track,
                    requester=requester,
                    source_name="stream",
                )
                for track in results
            ]
            return PlaylistResult(name="Stream Playlist", tracks=tracks)

        return [
            HarmoniXTrack(
                playable=results[0],
                requester=requester,
                source_name="stream",
            )
        ]
