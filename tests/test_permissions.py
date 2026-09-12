"""Unit tests for permissions and voice channel validations."""

import pytest
from unittest.mock import MagicMock
from utils.permissions import has_dj_permissions, check_voice_state
from bot.errors import UserNotInVoiceChannel, DifferentVoiceChannel, BotNotInVoiceChannel


def test_guild_owner_has_dj_permission(mock_member):
    mock_member.guild.owner_id = mock_member.id
    assert has_dj_permissions(mock_member) is True


def test_admin_has_dj_permission(mock_member):
    mock_member.guild.owner_id = 999999
    mock_member.guild_permissions.administrator = True
    assert has_dj_permissions(mock_member) is True


def test_dj_role_match(mock_member):
    mock_member.guild.owner_id = 999999
    mock_member.guild_permissions.administrator = False

    role = MagicMock()
    role.id = 555
    role.name = "DJ"
    mock_member.roles = [role]

    assert has_dj_permissions(mock_member, dj_role_id=555) is True
    assert has_dj_permissions(mock_member, dj_role_id=999) is True  # fallback role name "DJ"


def test_solo_listener_bypass(mock_member):
    mock_member.guild.owner_id = 999999
    mock_member.guild_permissions.administrator = False
    mock_member.roles = []

    # Alone with bot in voice channel
    mock_member.voice.channel.members = [mock_member]
    assert has_dj_permissions(mock_member, allow_solo=True) is True

    # With other listeners and no DJ role
    other_member = MagicMock()
    other_member.bot = False
    mock_member.voice.channel.members = [mock_member, other_member]
    assert has_dj_permissions(mock_member, allow_solo=True) is False


def test_voice_state_checks(mock_member):
    interaction = MagicMock()
    interaction.guild = mock_member.guild
    interaction.user = mock_member

    # User not in voice channel
    mock_member.voice = None
    with pytest.raises(UserNotInVoiceChannel):
        check_voice_state(interaction)

    # Bot not in voice when required
    mock_member.voice = MagicMock()
    mock_member.voice.channel.id = 123
    interaction.guild.voice_client = None
    with pytest.raises(BotNotInVoiceChannel):
        check_voice_state(interaction, require_bot=True)

    # Different channels
    bot_vc = MagicMock()
    bot_vc.channel.id = 456
    interaction.guild.voice_client = bot_vc
    with pytest.raises(DifferentVoiceChannel):
        check_voice_state(interaction, require_same_channel=True)
