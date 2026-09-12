"""Apple Music metadata source adapter."""

import re
from typing import Optional, List, Union
import aiohttp
import discord
import wavelink
from .base import BaseAudioSource, PlaylistResult
from music.track import HarmoniXTrack
from utils.validators import is_apple_music_url
from utils.logging import get_logger

logger = get_logger(__name__)


class AppleMusicSource(BaseAudioSource):
    """Adapter for resolving Apple Music links through metadata translation."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        super().__init__("applemusic")
        self._session = session

    def can_handle(self, query: str) -> bool:
        return is_apple_music_url(query)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def resolve(
        self,
        query: str,
        requester: Optional[discord.Member] = None,
        max_results: int = 10,
    ) -> Union[List[HarmoniXTrack], PlaylistResult]:
        session = await self._get_session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with session.get(query.strip(), headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()

                # Extract OpenGraph title and description
                title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)

                if not title_match:
                    return []

                raw_title = title_match.group(1)
                # Usually: "Song Name by Artist on Apple Music"
                clean_title = re.sub(r" on Apple Music.*$", "", raw_title)
                search_query = f"ytmsearch:{clean_title}"

                results = await wavelink.Playable.search(search_query)
                if not results:
                    return []

                target = results[0]
                return [
                    HarmoniXTrack(
                        playable=target,
                        requester=requester,
                        source_name="applemusic",
                    )
                ]

        except Exception as e:
            logger.error("Apple music metadata resolution failed: %s", e)
            return []
