"""Audio sources package."""

from .base import BaseAudioSource, PlaylistResult
from .youtube import YouTubeSource
from .spotify import SpotifySource
from .soundcloud import SoundCloudSource
from .apple_music import AppleMusicSource
from .direct_url import DirectURLSource

__all__ = [
    "BaseAudioSource",
    "PlaylistResult",
    "YouTubeSource",
    "SpotifySource",
    "SoundCloudSource",
    "AppleMusicSource",
    "DirectURLSource",
]
