"""Permission and voice state validation helpers."""

from typing import Optional
import discord
from discord import app_commands
from bot.errors import (
    UserNotInVoiceChannel,
    BotNotInVoiceChannel,
    DifferentVoiceChannel,
    DJRoleRequiredError,
)


def has_dj_permissions(
    member: discord.Member,
    dj_role_id: Optional[int] = None,
    allow_solo: bool = True,
) -> bool:
    """Verify if a member possesses DJ rights, administrator permissions, or guild ownership.
    If allow_solo is True and the member is alone with the bot in VC, allow DJ controls.
    """
    if not member or not hasattr(member, "guild") or member.guild is None:
        return False

    # Server owner and administrators always bypass DJ restrictions
    if member.guild.owner_id == member.id:
        return True
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True

    # Check DJ role
    if dj_role_id:
        if any(role.id == dj_role_id for role in member.roles):
            return True
    else:
        # Default fallback: check for any role named 'DJ' (case-insensitive)
        if any(role.name.lower() == "dj" for role in member.roles):
            return True

    # Solo listener exception: If the user is the only non-bot listener in the voice channel
    if allow_solo and member.voice and member.voice.channel:
        vc = member.voice.channel
        non_bot_members = [m for m in vc.members if not m.bot]
        if len(non_bot_members) == 1 and non_bot_members[0].id == member.id:
            return True

    return False


def check_voice_state(
    interaction: discord.Interaction,
    require_bot: bool = False,
    require_same_channel: bool = True,
) -> None:
    """Verify the voice state of the user and bot.
    Raises custom exceptions if verification fails.
    """
    if not interaction.guild or not hasattr(interaction.user, "guild") or interaction.user.guild is None:
        raise UserNotInVoiceChannel("This command can only be used inside a server.")

    user_voice = interaction.user.voice
    if not user_voice or not user_voice.channel:
        raise UserNotInVoiceChannel("You must be connected to a voice channel to use this.")

    bot_voice = interaction.guild.voice_client

    if require_bot and not bot_voice:
        raise BotNotInVoiceChannel("I am not currently connected to any voice channel.")

    if bot_voice and require_same_channel and bot_voice.channel:
        if user_voice.channel.id != bot_voice.channel.id:
            raise DifferentVoiceChannel(
                f"You must be in the same voice channel ({bot_voice.channel.mention}) as me."
            )


def require_voice(require_same_channel: bool = True):
    """App command check decorator enforcing voice channel presence."""
    async def predicate(interaction: discord.Interaction) -> bool:
        check_voice_state(interaction, require_bot=False, require_same_channel=require_same_channel)
        return True
    return app_commands.check(predicate)


def require_dj(allow_solo: bool = True):
    """App command check decorator enforcing DJ or Admin permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise DJRoleRequiredError()

        # Check repository settings if available via client
        dj_role_id = None
        if hasattr(interaction.client, "db") and interaction.client.db:
            settings = await interaction.client.db.get_guild_settings(interaction.guild.id)
            if settings:
                dj_role_id = settings.get("dj_role_id")

        if not has_dj_permissions(interaction.user, dj_role_id=dj_role_id, allow_solo=allow_solo):
            raise DJRoleRequiredError()
        return True

    return app_commands.check(predicate)
