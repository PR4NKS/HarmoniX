"""Services package."""

from .lyrics import LyricsService
from .metadata import MetadataService
from .recommendations import RecommendationService
from .statistics import StatisticsService

__all__ = [
    "LyricsService",
    "MetadataService",
    "RecommendationService",
    "StatisticsService",
]
