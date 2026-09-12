"""Service providing formatted metadata for tracks, albums, and artists."""

from typing import Dict, Any, Optional
from music.track import HarmoniXTrack
from utils.validators import format_duration


class MetadataService:
    """Provides structured presentation details for tracks and media."""

    @staticmethod
    def get_track_details(track: HarmoniXTrack) -> Dict[str, Any]:
        """Extract comprehensive track metadata fields."""
        return {
            "title": track.title,
            "artist": track.author,
            "album": track.album,
            "duration": format_duration(track.length),
            "raw_duration_ms": track.length,
            "uri": track.uri,
            "artwork": track.artwork,
            "source": track.source_name.title(),
            "requester": track.requester_mention,
        }
