"""Unit tests for player models, filters, embeds, and SQLite repository."""

import pytest
from music.track import HarmoniXTrack
from music.filters import FilterPreset, apply_preset
from ui.embeds import create_track_queued_embed, create_success_embed, create_error_embed
from database.connection import DatabaseManager
from database.repository import MusicRepository
import wavelink


def test_harmonix_track_wrapper(mock_playable_factory, mock_member):
    p = mock_playable_factory(title="My Song", author="My Artist", length=125000)
    track = HarmoniXTrack(playable=p, requester=mock_member, album="Hit Album", source_name="youtube")

    assert track.title == "My Song"
    assert track.author == "My Artist"
    assert track.duration_str == "02:05"
    assert track.album == "Hit Album"
    assert track.requester_name == "TestUser"

    dump = track.to_dict()
    assert dump["title"] == "My Song"
    assert dump["requester_id"] == mock_member.id


def test_filter_presets():
    filters = wavelink.Filters()
    apply_preset(filters, FilterPreset.NIGHTCORE)
    assert filters.timescale.payload["pitch"] == 1.3
    assert filters.timescale.payload["speed"] == 1.25

    apply_preset(filters, FilterPreset.FLAT)
    assert filters.timescale.payload == {}


def test_embed_builders(mock_playable_factory, mock_member):
    p = mock_playable_factory(title="Echoes", author="Pink Floyd", length=300000)
    track = HarmoniXTrack(playable=p, requester=mock_member)

    embed = create_track_queued_embed(track, position=1)
    assert embed.title == "Added to Queue"
    assert "Echoes" in embed.description

    err_embed = create_error_embed("Error", "Something went wrong")
    assert "❌ Error" in err_embed.title


@pytest.mark.asyncio
async def test_database_repository(tmp_path):
    db_file = tmp_path / "test.db"
    db_mgr = DatabaseManager(str(db_file))
    await db_mgr.connect()
    repo = MusicRepository(db_mgr)

    # 1. Guild settings
    cfg = await repo.get_guild_settings(guild_id=101)
    assert cfg.guild_id == 101
    assert cfg.default_volume == 80

    await repo.update_guild_settings(guild_id=101, default_volume=65, mode_247=True)
    cfg2 = await repo.get_guild_settings(guild_id=101)
    assert cfg2.default_volume == 65
    assert cfg2.mode_247 is True

    # 2. Favorites
    added = await repo.add_favorite(
        user_id=1,
        title="Song A",
        uri="https://youtube.com/watch?v=A",
        author="Artist A",
        duration=180000,
    )
    assert added is True

    favs = await repo.get_favorites(user_id=1)
    assert len(favs) == 1
    assert favs[0].title == "Song A"

    # 3. Playlists
    pl_id = await repo.create_playlist(user_id=1, name="Rock Hits", is_public=True)
    assert pl_id is not None

    await repo.add_track_to_playlist(
        playlist_id=pl_id,
        title="Rock 1",
        uri="https://youtube.com/watch?v=R1",
        author="Band",
        duration=200000,
    )
    pl = await repo.get_playlist_by_name(user_id=1, name="Rock Hits")
    assert pl is not None
    assert len(pl.tracks) == 1

    await db_mgr.close()
