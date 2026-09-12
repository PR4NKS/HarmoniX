"""Recommendation service for generating related song queues and autoplay tracks."""

from typing import List, Optional
import discord
import wavelink
from music.track import HarmoniXTrack
from utils.logging import get_logger

logger = get_logger(__name__)


class RecommendationService:
    """Discovers related music tracks based on seed tracks."""

    @staticmethod
    async def get_related_tracks(
        seed_track: HarmoniXTrack,
        limit: int = 5,
        requester: Optional[discord.Member] = None,
    ) -> List[HarmoniXTrack]:
        """Search for tracks related to the seed artist and title."""
        query = f"ytmsearch:{seed_track.author} {seed_track.title}"
        results = await wavelink.Playable.search(query)
        if not results:
            return []

        recommended: List[HarmoniXTrack] = []
        for item in results:
            if item.uri != seed_track.uri:
                recommended.append(
                    HarmoniXTrack(
                        playable=item,
                        requester=requester,
                        album=None,
                        source_name="recommendation",
                    )
                )
                if len(recommended) >= limit:
                    break

        return recommended
