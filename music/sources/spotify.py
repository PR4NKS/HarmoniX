"""Spotify metadata adapter with official Web API client credentials and search fallback."""

import asyncio
import base64
import re
import time
from typing import Optional, List, Union, Dict, Any
import aiohttp
import discord
import wavelink
from .base import BaseAudioSource, PlaylistResult
from music.track import HarmoniXTrack
from utils.validators import is_spotify_url
from utils.logging import get_logger

logger = get_logger(__name__)


class SpotifySource(BaseAudioSource):
    """Adapter for resolving Spotify tracks, playlists, and albums via metadata translation."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        super().__init__("spotify")
        self.client_id = client_id
        self.client_secret = client_secret
        self._session = session
        self._token: Optional[str] = None
        self._token_expires: float = 0
        self._lock = asyncio.Lock()

    def can_handle(self, query: str) -> bool:
        return is_spotify_url(query)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_access_token(self) -> Optional[str]:
        """Obtain or refresh Spotify OAuth client credentials token."""
        if not self.client_id or not self.client_secret:
            return None

        async with self._lock:
            if self._token and time.time() < self._token_expires - 60:
                return self._token

            session = await self._get_session()
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"grant_type": "client_credentials"}

            try:
                async with session.post(
                    "https://accounts.spotify.com/api/token",
                    headers=headers,
                    data=data,
                    timeout=10,
                ) as resp:
                    if resp.status == 200:
                        payload = await resp.json()
                        self._token = payload.get("access_token")
                        expires_in = payload.get("expires_in", 3600)
                        self._token_expires = time.time() + expires_in
                        return self._token
                    else:
                        logger.warning("Spotify token error: status %d", resp.status)
                        return None
            except Exception as e:
                logger.error("Failed to fetch Spotify access token: %s", e)
                return None

    def _parse_url(self, url: str) -> Optional[tuple[str, str]]:
        """Extract resource type and ID from Spotify URL."""
        match = re.search(r"open\.spotify\.com/(track|playlist|album|artist)/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1), match.group(2)
        return None

    async def resolve(
        self,
        query: str,
        requester: Optional[discord.Member] = None,
        max_results: int = 100,
    ) -> Union[List[HarmoniXTrack], PlaylistResult]:
        parsed = self._parse_url(query)
        if not parsed:
            return []

        item_type, item_id = parsed
        token = await self._get_access_token()

        if token:
            result = await self._resolve_api(item_type, item_id, token, requester, max_results)
            if result:
                return result

        # Embed scraper fallback (supports mixes, curated playlists, albums, and tracks without API tokens)
        embed_result = await self._scrape_embed(query, item_type, item_id, requester, max_results)
        if embed_result:
            return embed_result

        # Final fallback: oembed
        return await self._resolve_oembed(query, item_type, requester)

    async def _resolve_api(
        self,
        item_type: str,
        item_id: str,
        token: str,
        requester: Optional[discord.Member],
        max_results: int,
    ) -> Union[List[HarmoniXTrack], PlaylistResult]:
        session = await self._get_session()
        headers = {"Authorization": f"Bearer {token}"}

        try:
            if item_type == "track":
                url = f"https://api.spotify.com/v1/tracks/{item_id}"
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    track = await self._search_playable(
                        title=data["name"],
                        artist=data["artists"][0]["name"],
                        album=data.get("album", {}).get("name"),
                        requester=requester,
                    )
                    return [track] if track else []

            elif item_type in ("playlist", "album"):
                endpoint = f"https://api.spotify.com/v1/{item_type}s/{item_id}"
                async with session.get(endpoint, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    name = data.get("name", "Spotify Playlist")
                    items = data.get("tracks", {}).get("items", [])
                    raw_tracks = []
                    for item in items[:max_results]:
                        t_data = item.get("track", item)
                        if t_data and "name" in t_data and t_data.get("artists"):
                            raw_tracks.append({
                                "title": t_data["name"],
                                "artist": t_data["artists"][0]["name"],
                                "album": t_data.get("album", {}).get("name", name),
                            })

                    resolved_tracks = await self._batch_resolve(raw_tracks, requester)
                    return PlaylistResult(name=name, tracks=resolved_tracks)

            elif item_type == "artist":
                endpoint = f"https://api.spotify.com/v1/artists/{item_id}/top-tracks?market=US"
                async with session.get(endpoint, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    tracks = data.get("tracks", [])
                    raw_tracks = [
                        {
                            "title": t["name"],
                            "artist": t["artists"][0]["name"],
                            "album": t.get("album", {}).get("name"),
                        }
                        for t in tracks[:max_results]
                    ]
                    resolved_tracks = await self._batch_resolve(raw_tracks, requester)
                    return PlaylistResult(name=f"Top Tracks: {raw_tracks[0]['artist']}", tracks=resolved_tracks)

        except Exception as e:
            logger.error("Spotify API resolution failed: %s", e)
            return []

        return []

    async def _scrape_embed(
        self,
        url: str,
        item_type: str,
        item_id: str,
        requester: Optional[discord.Member],
        max_results: int,
    ) -> Union[List[HarmoniXTrack], PlaylistResult, None]:
        """Scrape Spotify public embed page to extract tracks without requiring API tokens."""
        session = await self._get_session()
        embed_url = f"https://open.spotify.com/embed/{item_type}/{item_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            async with session.get(embed_url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

            match = re.search(r'<script\s+id=[\'"]__NEXT_DATA__[\'"]\s+type=[\'"]application/json[\'"]>(.*?)</script>', html)
            if not match:
                return None

            import json
            payload = json.loads(match.group(1))
            entity = payload.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
            if not entity:
                return None

            name = entity.get("name") or entity.get("title") or "Spotify Playlist"
            track_list = entity.get("trackList", [])

            if track_list:
                raw_tracks = []
                for item in track_list[:max_results]:
                    t_title = item.get("title")
                    t_artist = item.get("subtitle", "")
                    if t_title:
                        raw_tracks.append({
                            "title": t_title,
                            "artist": t_artist,
                            "album": name,
                        })
                resolved_tracks = await self._batch_resolve(raw_tracks, requester)
                if resolved_tracks:
                    return PlaylistResult(name=name, tracks=resolved_tracks)
            elif item_type == "track":
                title = entity.get("title") or entity.get("name")
                artists = entity.get("artists", [])
                artist_name = artists[0].get("name", "") if artists else entity.get("subtitle", "")
                if title:
                    track = await self._search_playable(title=title, artist=artist_name, requester=requester)
                    return [track] if track else None
        except Exception as e:
            logger.warning("Spotify embed scraper error for %s: %s", url, e)
        return None

    async def _resolve_oembed(
        self,
        url: str,
        item_type: str,
        requester: Optional[discord.Member],
    ) -> List[HarmoniXTrack]:
        """Fallback for when Spotify API credentials are not configured."""
        session = await self._get_session()
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        try:
            async with session.get(oembed_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    title = data.get("title", "")
                    # Usually "Song Title - Artist Name"
                    if " - " in title:
                        parts = title.split(" - ", 1)
                        track = await self._search_playable(title=parts[0], artist=parts[1], requester=requester)
                    else:
                        track = await self._search_playable(title=title, artist="", requester=requester)
                    return [track] if track else []
        except Exception as e:
            logger.warning("Spotify oEmbed fallback failed: %s", e)
        return []

    async def _search_playable(
        self,
        title: str,
        artist: str,
        album: Optional[str] = None,
        requester: Optional[discord.Member] = None,
    ) -> Optional[HarmoniXTrack]:
        """Search for a track via Lavalink audio engine with Spotify metadata."""
        from services.stream_server import get_stream_server
        server = get_stream_server()

        query_text = f"{title} {artist}".strip()
        if server and server.is_running:
            try:
                track = await server.resolve_playable(query_text, requester=requester)
                if track:
                    track.album = album or "Spotify Track"
                    track.source_name = "spotify"
                    return track
            except Exception as e:
                logger.debug("Stream server search fallback for Spotify track %s: %s", title, e)

        query = f"ytmsearch:{query_text}"
        try:
            results = await wavelink.Playable.search(query)
            if results:
                target = results[0]
                return HarmoniXTrack(
                    playable=target,
                    requester=requester,
                    album=album,
                    source_name="spotify",
                )
        except Exception as e:
            logger.debug("Failed search for Spotify track %s: %s", title, e)
        return None

    async def _batch_resolve(
        self,
        items: List[Dict[str, Any]],
        requester: Optional[discord.Member],
        batch_size: int = 5,
    ) -> List[HarmoniXTrack]:
        """Concurrently resolve a list of metadata items to playable tracks."""
        resolved: List[HarmoniXTrack] = []
        for i in range(0, len(items), batch_size):
            chunk = items[i : i + batch_size]
            tasks = [
                self._search_playable(
                    title=item["title"],
                    artist=item["artist"],
                    album=item.get("album"),
                    requester=requester,
                )
                for item in chunk
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in batch_results:
                if isinstance(res, HarmoniXTrack):
                    resolved.append(res)
        return resolved
