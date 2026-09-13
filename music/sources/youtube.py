"""YouTube and YouTube Music source adapter."""

import asyncio
from typing import Optional, List, Union
import discord
import wavelink
from .base import BaseAudioSource, PlaylistResult
from music.track import HarmoniXTrack
from utils.validators import is_youtube_url, is_valid_url, sanitize_youtube_url
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
        query_str = sanitize_youtube_url(query.strip())

        # 1. Direct YouTube URLs (Single Video or Playlist)
        if is_youtube_url(query_str):
            from services.stream_server import get_stream_server
            server = get_stream_server()

            # Check if this is a YouTube playlist
            if "playlist?list=" in query_str:
                try:
                    import yt_dlp
                    loop = asyncio.get_running_loop()

                    def extract_pl():
                        ydl_opts = {
                            "extract_flat": True,
                            "quiet": True,
                            "no_warnings": True,
                            "skip_download": True,
                        }
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            return ydl.extract_info(query_str, download=False)

                    pl_data = await loop.run_in_executor(None, extract_pl)
                    if pl_data and "entries" in pl_data:
                        pl_title = pl_data.get("title", "YouTube Playlist")
                        entries = [e for e in pl_data["entries"] if e and e.get("id")][:max_results]
                        resolved_tracks = []
                        for entry in entries:
                            vid = entry.get("id")
                            if server and server.is_running:
                                t = await server.resolve_playable(vid, requester=requester)
                                if t:
                                    resolved_tracks.append(t)
                                    continue
                            # Fallback to direct search if stream server not ready
                            try:
                                res = await wavelink.Playable.search(f"https://www.youtube.com/watch?v={vid}")
                                if res:
                                    resolved_tracks.append(
                                        HarmoniXTrack(
                                            playable=res[0],
                                            requester=requester,
                                            source_name="youtube",
                                        )
                                    )
                            except Exception:
                                pass
                        if resolved_tracks:
                            return PlaylistResult(name=pl_title, tracks=resolved_tracks)
                except Exception as pl_err:
                    logger.warning("Failed extracting YouTube playlist with yt-dlp: %s", pl_err)

            # Single Video YouTube URL - prioritize stream server to guarantee 100% playback
            if server and server.is_running:
                try:
                    stream_track = await server.resolve_playable(query_str, requester=requester)
                    if stream_track:
                        return [stream_track]
                except Exception as stream_err:
                    logger.warning("Stream server direct resolution error: %s", stream_err)

            # Fallback to Lavalink direct search if stream server unavailable
            try:
                results = await wavelink.Playable.search(query_str)
                if results:
                    tracks = [
                        HarmoniXTrack(
                            playable=r,
                            requester=requester,
                            source_name=getattr(r, "source", "unknown"),
                        )
                        for r in results[:max_results]
                    ]
                    return tracks
            except Exception as e:
                logger.warning("Lavalink direct URL resolution failed for %s: %s", query_str, e)
                results = None

        elif is_valid_url(query_str):
            try:
                results = await wavelink.Playable.search(query_str)
            except Exception as e:
                logger.warning("Lavalink direct URL resolution failed for %s: %s", query_str, e)
                results = None
        else:
            from services.stream_server import get_stream_server
            server = get_stream_server()
            if server and server.is_running:
                try:
                    stream_track = await server.resolve_playable(query_str, requester=requester)
                    if stream_track:
                        return [stream_track]
                except Exception as stream_err:
                    logger.debug("Stream server search error for '%s': %s", query_str, stream_err)

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
