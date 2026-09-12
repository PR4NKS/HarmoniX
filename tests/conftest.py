"""Shared test fixtures, mocks, and test utilities."""

import pytest
from unittest.mock import MagicMock, AsyncMock
import wavelink
from music.track import HarmoniXTrack


class FakePlayable:
    """Mock Wavelink Playable object for unit testing."""

    def __init__(
        self,
        title: str = "Test Title",
        author: str = "Test Artist",
        length: int = 180000,
        uri: str = "https://youtube.com/watch?v=mock123",
        identifier: str = "mock123",
        artwork: str = "https://example.com/artwork.jpg",
        source: str = "youtube",
    ):
        self.title = title
        self.author = author
        self.length = length
        self.uri = uri
        self.identifier = identifier
        self.artwork = artwork
        self.source = source


@pytest.fixture
def mock_playable_factory():
    """Factory to create fake playables with unique titles and identifiers."""
    def _create(title="Track", author="Artist", length=180000, uri="https://youtube.com/watch?v=1"):
        return FakePlayable(title=title, author=author, length=length, uri=uri)
    return _create


@pytest.fixture
def mock_member():
    """Mock Discord member."""
    member = MagicMock()
    member.id = 123456789
    member.name = "TestUser"
    member.display_name = "TestUser"
    member.mention = "<@123456789>"
    member.bot = False
    member.guild.owner_id = 999999999
    member.guild_permissions.administrator = False
    member.guild_permissions.manage_guild = False
    member.roles = []
    member.voice = MagicMock()
    member.voice.channel = MagicMock()
    member.voice.channel.id = 111
    member.voice.channel.members = [member]
    return member
