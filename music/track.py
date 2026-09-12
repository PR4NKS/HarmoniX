"""Enhanced track representation wrapping or annotating Wavelink Playable."""

from typing import Optional, Dict, Any
import discord
import wavelink
from utils.validators import format_duration


class HarmoniXTrack:
    """Wrapper around wavelink.Playable providing unified metadata and requester tracking."""

    def __init__(
        self,
        playable: wavelink.Playable,
        requester: Optional[discord.Member] = None,
        album: Optional[str] = None,
        source_name: Optional[str] = None,
    ):
        self.playable = playable
        self.requester = requester
        self.album = album or "Unknown Album"
        self.source_name = source_name or getattr(playable, "source", "unknown")

    @property
    def title(self) -> str:
        return getattr(self.playable, "title", "Unknown Title")

    @property
    def author(self) -> str:
        return getattr(self.playable, "author", "Unknown Artist")

    @property
    def length(self) -> int:
        """Length in milliseconds."""
        return getattr(self.playable, "length", 0)

    @property
    def uri(self) -> str:
        return getattr(self.playable, "uri", "") or ""

    @property
    def identifier(self) -> str:
        return getattr(self.playable, "identifier", "")

    @property
    def artwork(self) -> Optional[str]:
        return getattr(self.playable, "artwork", None)

    @property
    def duration_str(self) -> str:
        return format_duration(self.length)

    @property
    def requester_mention(self) -> str:
        if self.requester:
            return self.requester.mention
        return "Autoplay"

    @property
    def requester_name(self) -> str:
        if self.requester:
            return getattr(self.requester, "display_name", str(self.requester))
        return "Autoplay"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize track for saved queue storage."""
        return {
            "title": self.title,
            "author": self.author,
            "length": self.length,
            "uri": self.uri,
            "identifier": self.identifier,
            "artwork": self.artwork,
            "album": self.album,
            "source_name": self.source_name,
            "requester_id": self.requester.id if self.requester else None,
        }

    def __repr__(self) -> str:
        return f"<HarmoniXTrack title={self.title!r} author={self.author!r} duration={self.duration_str}>"
