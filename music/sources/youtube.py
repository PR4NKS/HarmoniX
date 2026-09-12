"""YouTube and YouTube Music source adapter."""

from typing import Optional, List, Union
import discord
import wavelink
from .base import BaseAudioSource, PlaylistResult
from music.track import HarmoniXTrack
from utils.validators import is_youtube_url, is_valid_url
from utils.logging import get_logger

logger = get_logger(__name__)


class YouTubeSource(BaseAudioSource):
    """Adapter for resolving YouTube tracks, searches, and playlists via Lavalink."""

    def __init__(self, default_search_type: str = "ytmsearch"):
        super().__init__("youtube")
        self.default_search_type = default_search_type

    def can_handle(self, query: str) -> bool:
        # Handles YouTube URLs or standard text search queries
        if is_youtube_url(query):
            return True
        # Plain search queries (not other platform URLs)
        if not is_valid_url(query):
            return True
        return False

    async def resolve(
        self,
        query: str,
        requester: Optional[discord.Member] = None,
        max_results: int = 10,
    ) -> Union[List[HarmoniXTrack], PlaylistResult]:
        query_str = query.strip()

        if is_valid_url(query_str):
            results = await wavelink.Playable.search(query_str)
        else:
            # Determine search order based on configuration
            if "sc" in self.default_search_type.lower():
                primary_source = wavelink.TrackSource.SoundCloud
                secondary_source = wavelink.TrackSource.YouTubeMusic
            else:
                primary_source = wavelink.TrackSource.YouTubeMusic
                secondary_source = wavelink.TrackSource.SoundCloud

            try:
                results = await wavelink.Playable.search(query_str, source=primary_source)
            except Exception as err:
                logger.warning("Primary search for '%s' (%s) failed: %s", query_str, primary_source, err)
                results = None

            if not results:
                try:
                    results = await wavelink.Playable.search(query_str, source=secondary_source)
                except Exception as err:
                    logger.warning("Secondary search for '%s' (%s) failed: %s", query_str, secondary_source, err)
                    results = None

        if not results:
            return []

        if isinstance(results, wavelink.Playlist):
            playlist_name = getattr(results, "name", "Playlist")
            tracks = [
                HarmoniXTrack(
                    playable=track,
                    requester=requester,
                    source_name=getattr(track, "source", "unknown"),
                )
                for track in results
            ]
            return PlaylistResult(name=playlist_name, tracks=tracks)

        # List of results
        tracks = []
        for track in results[:max_results]:
            tracks.append(
                HarmoniXTrack(
                    playable=track,
                    requester=requester,
                    source_name=getattr(track, "source", "unknown"),
                )
            )
        return tracks
