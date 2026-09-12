"""Abstract base class for audio source adapters."""

from abc import ABC, abstractmethod
from typing import Optional, List, Union
import discord
from music.track import HarmoniXTrack


class PlaylistResult:
    """Represents a loaded playlist container."""

    def __init__(self, name: str, tracks: List[HarmoniXTrack], selected_index: int = 0):
        self.name = name
        self.tracks = tracks
        self.selected_index = selected_index

    def __len__(self) -> int:
        return len(self.tracks)

    def __repr__(self) -> str:
        return f"<PlaylistResult name={self.name!r} track_count={len(self.tracks)}>"


class BaseAudioSource(ABC):
    """Abstract audio source interface."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Return True if this source adapter is designed to handle the given query/URL."""
        pass

    @abstractmethod
    async def resolve(
        self,
        query: str,
        requester: Optional[discord.Member] = None,
        max_results: int = 10,
    ) -> Union[List[HarmoniXTrack], PlaylistResult]:
        """Resolve a query or URL into HarmoniX tracks or a PlaylistResult."""
        pass
