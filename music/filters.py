"""Audio filter presets and equalizer configuration for Lavalink / Wavelink."""

from enum import Enum
from typing import Dict, Any, List
import wavelink


class FilterPreset(Enum):
    FLAT = "flat"
    HIFI = "hifi"
    BASSBOOST_LOW = "bassboost_low"
    BASSBOOST_MED = "bassboost_med"
    BASSBOOST_HIGH = "bassboost_high"
    NIGHTCORE = "nightcore"
    VAPORWAVE = "vaporwave"
    ROTATION_8D = "8d"
    KARAOKE = "karaoke"
    TREMOLO = "tremolo"
    VIBRATO = "vibrato"
    POP = "pop"
    ROCK = "rock"
    ELECTRONIC = "electronic"


# Equalizer band definitions (-0.25 to 1.0 gain)
HIFI_STUDIO_BANDS = [
    {"band": 0, "gain": 0.08},
    {"band": 1, "gain": 0.06},
    {"band": 2, "gain": 0.03},
    {"band": 3, "gain": 0.00},
    {"band": 4, "gain": -0.02},
    {"band": 5, "gain": -0.02},
    {"band": 6, "gain": 0.00},
    {"band": 7, "gain": 0.02},
    {"band": 8, "gain": 0.04},
    {"band": 9, "gain": 0.06},
    {"band": 10, "gain": 0.08},
    {"band": 11, "gain": 0.10},
    {"band": 12, "gain": 0.12},
    {"band": 13, "gain": 0.12},
    {"band": 14, "gain": 0.10},
]

BASSBOOST_LOW_BANDS = [
    {"band": 0, "gain": 0.15},
    {"band": 1, "gain": 0.10},
    {"band": 2, "gain": 0.05},
]

BASSBOOST_MED_BANDS = [
    {"band": 0, "gain": 0.30},
    {"band": 1, "gain": 0.20},
    {"band": 2, "gain": 0.12},
    {"band": 3, "gain": 0.05},
]

BASSBOOST_HIGH_BANDS = [
    {"band": 0, "gain": 0.45},
    {"band": 1, "gain": 0.35},
    {"band": 2, "gain": 0.25},
    {"band": 3, "gain": 0.15},
]

POP_BANDS = [
    {"band": 0, "gain": -0.05},
    {"band": 1, "gain": 0.05},
    {"band": 2, "gain": 0.15},
    {"band": 3, "gain": 0.20},
    {"band": 4, "gain": 0.15},
    {"band": 5, "gain": 0.05},
]

ROCK_BANDS = [
    {"band": 0, "gain": 0.20},
    {"band": 1, "gain": 0.15},
    {"band": 2, "gain": -0.05},
    {"band": 3, "gain": -0.10},
    {"band": 4, "gain": 0.05},
    {"band": 5, "gain": 0.15},
    {"band": 6, "gain": 0.25},
]

ELECTRONIC_BANDS = [
    {"band": 0, "gain": 0.30},
    {"band": 1, "gain": 0.20},
    {"band": 2, "gain": 0.0},
    {"band": 3, "gain": -0.05},
    {"band": 4, "gain": 0.10},
    {"band": 5, "gain": 0.20},
]


def apply_preset(filters: wavelink.Filters, preset: FilterPreset) -> wavelink.Filters:
    """Apply a preset configuration to the given Wavelink Filters instance."""
    filters.reset()

    if preset == FilterPreset.FLAT:
        return filters

    elif preset == FilterPreset.HIFI:
        filters.equalizer.set(bands=HIFI_STUDIO_BANDS)

    elif preset == FilterPreset.BASSBOOST_LOW:
        filters.equalizer.set(bands=BASSBOOST_LOW_BANDS)

    elif preset == FilterPreset.BASSBOOST_MED:
        filters.equalizer.set(bands=BASSBOOST_MED_BANDS)

    elif preset == FilterPreset.BASSBOOST_HIGH:
        filters.equalizer.set(bands=BASSBOOST_HIGH_BANDS)

    elif preset == FilterPreset.NIGHTCORE:
        filters.timescale.set(pitch=1.3, speed=1.25, rate=1.0)

    elif preset == FilterPreset.VAPORWAVE:
        filters.timescale.set(pitch=0.8, speed=0.85, rate=1.0)

    elif preset == FilterPreset.ROTATION_8D:
        filters.rotation.set(rotation_hz=0.2)

    elif preset == FilterPreset.KARAOKE:
        filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)

    elif preset == FilterPreset.TREMOLO:
        filters.tremolo.set(frequency=2.0, depth=0.5)

    elif preset == FilterPreset.VIBRATO:
        filters.vibrato.set(frequency=2.0, depth=0.5)

    elif preset == FilterPreset.POP:
        filters.equalizer.set(bands=POP_BANDS)

    elif preset == FilterPreset.ROCK:
        filters.equalizer.set(bands=ROCK_BANDS)

    elif preset == FilterPreset.ELECTRONIC:
        filters.equalizer.set(bands=ELECTRONIC_BANDS)

    return filters
