"""Lyrics service supporting plain and synchronized lyrics with caching."""

import asyncio
from typing import Optional, Dict, Any, List
import aiohttp
from utils.logging import get_logger

logger = get_logger(__name__)


class LyricsService:
    """Fetches song lyrics using LRCLIB API and Genius fallback."""

    def __init__(self, genius_token: Optional[str] = None):
        self.genius_token = genius_token
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_lyrics(
        self,
        title: str,
        artist: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Look up lyrics. Returns dict with {title, artist, plain_lyrics, synced_lyrics}."""
        cache_key = f"{title.lower()}|{(artist or '').lower()}"

        async with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        # 1. Query LRCLIB (free, high quality, synced lyrics)
        result = await self._fetch_lrclib(title, artist, duration_seconds)

        # 2. Fallback to Genius if needed and token available
        if not result and self.genius_token:
            result = await self._fetch_genius(title, artist)

        if result:
            async with self._cache_lock:
                # Keep cache bounded to 100 items
                if len(self._cache) > 100:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[cache_key] = result

        return result

    async def _fetch_lrclib(
        self,
        title: str,
        artist: Optional[str],
        duration: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        session = await self._get_session()
        url = "https://lrclib.net/api/get"
        params = {"track_name": title}
        if artist:
            params["artist_name"] = artist
        if duration:
            params["duration"] = str(duration)

        headers = {"User-Agent": "HarmoniX-Discord-Music-Bot/1.0 (https://github.com/HarmoniX)"}

        try:
            async with session.get(url, params=params, headers=headers, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lyrics = data.get("plainLyrics") or data.get("syncedLyrics")
                    if lyrics:
                        return {
                            "title": data.get("trackName", title),
                            "artist": data.get("artistName", artist or "Unknown"),
                            "plain_lyrics": data.get("plainLyrics", ""),
                            "synced_lyrics": data.get("syncedLyrics"),
                            "source": "LRCLIB",
                        }
        except Exception as e:
            logger.debug("LRCLIB lookup failed for %s: %s", title, e)

        # If strict get fails, try search endpoint on LRCLIB
        try:
            search_url = "https://lrclib.net/api/search"
            q = f"{title} {artist}" if artist else title
            async with session.get(search_url, params={"q": q}, headers=headers, timeout=8) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    if results and isinstance(results, list):
                        top = results[0]
                        return {
                            "title": top.get("trackName", title),
                            "artist": top.get("artistName", artist or "Unknown"),
                            "plain_lyrics": top.get("plainLyrics", ""),
                            "synced_lyrics": top.get("syncedLyrics"),
                            "source": "LRCLIB",
                        }
        except Exception as e:
            logger.debug("LRCLIB search failed for %s: %s", title, e)

        return None

    async def _fetch_genius(self, title: str, artist: Optional[str]) -> Optional[Dict[str, Any]]:
        session = await self._get_session()
        query = f"{title} {artist}" if artist else title
        headers = {"Authorization": f"Bearer {self.genius_token}"}

        try:
            async with session.get(
                "https://api.genius.com/search",
                params={"q": query},
                headers=headers,
                timeout=8,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    hits = data.get("response", {}).get("hits", [])
                    if hits:
                        hit = hits[0]["result"]
                        return {
                            "title": hit.get("title", title),
                            "artist": hit.get("primary_artist", {}).get("name", artist or "Unknown"),
                            "url": hit.get("url"),
                            "plain_lyrics": f"View full lyrics on Genius: {hit.get('url')}",
                            "source": "Genius",
                        }
        except Exception as e:
            logger.debug("Genius API lookup failed: %s", e)

        return None

    @staticmethod
    def paginate_lyrics(lyrics_text: str, max_chars: int = 1500) -> List[str]:
        """Split long lyrics into readable pages preserving stanza boundaries."""
        if not lyrics_text:
            return ["No lyrics found for this track."]

        lines = lyrics_text.split("\n")
        pages: List[str] = []
        current_page: List[str] = []
        current_len = 0

        for line in lines:
            line_len = len(line) + 1
            if current_len + line_len > max_chars and current_page:
                pages.append("\n".join(current_page))
                current_page = [line]
                current_len = line_len
            else:
                current_page.append(line)
                current_len += line_len

        if current_page:
            pages.append("\n".join(current_page))

        return pages or [lyrics_text]
