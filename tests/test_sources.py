"""Unit tests for URL validators, time formatting, and source routing."""

import pytest
from utils.validators import (
    is_valid_url,
    is_youtube_url,
    is_spotify_url,
    is_soundcloud_url,
    is_apple_music_url,
    format_duration,
    parse_time_to_seconds,
    create_progress_bar,
)
from music.sources import (
    YouTubeSource,
    SpotifySource,
    SoundCloudSource,
    AppleMusicSource,
    DirectURLSource,
)


def test_url_detection():
    yt_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    sp_url = "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"
    sc_url = "https://soundcloud.com/artist-name/track-name"
    am_url = "https://music.apple.com/us/album/song-name/12345"
    stream_url = "https://stream.zeno.fm/f3wvbbqmdg8uv.mp3"

    assert is_youtube_url(yt_url) is True
    assert is_spotify_url(sp_url) is True
    assert is_soundcloud_url(sc_url) is True
    assert is_apple_music_url(am_url) is True
    assert is_valid_url(stream_url) is True


def test_source_adapter_routing():
    yt = YouTubeSource()
    sp = SpotifySource()
    sc = SoundCloudSource()
    am = AppleMusicSource()
    direct = DirectURLSource()

    assert yt.can_handle("never gonna give you up") is True
    assert yt.can_handle("https://www.youtube.com/watch?v=12345678901") is True
    assert sp.can_handle("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT") is True
    assert sc.can_handle("https://soundcloud.com/artist/track") is True
    assert am.can_handle("https://music.apple.com/us/album/song/123") is True
    assert direct.can_handle("http://relay.radio.com/live.mp3") is True


def test_duration_formatting():
    assert format_duration(0) == "00:00"
    assert format_duration(65000) == "01:05"
    assert format_duration(3665000) == "01:01:05"
    assert format_duration(86400000 * 3) == "🔴 LIVE"


def test_time_parsing():
    assert parse_time_to_seconds("90") == 90
    assert parse_time_to_seconds("1:30") == 90
    assert parse_time_to_seconds("01:00:00") == 3600
    assert parse_time_to_seconds("2m 15s") == 135
    assert parse_time_to_seconds("invalid") is None


def test_progress_bar():
    bar = create_progress_bar(50, 100, length=10)
    assert "🔘" in bar
    assert len(bar) == 10
