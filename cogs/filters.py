"""Audio effects, equalizer presets, and filter controls."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from music.player import HarmoniXPlayer
from music.filters import FilterPreset
from utils.permissions import check_voice_state
from ui.embeds import create_success_embed, create_info_embed
from bot.errors import BotNotInVoiceChannel

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class FiltersCog(commands.Cog, name="Filters"):
    """Audio DSP filters, equalizer presets, and effects."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    filter_group = app_commands.Group(name="filter", description="Audio effects and equalizer presets")

    @filter_group.command(name="hifi", description="Enable High-Fidelity Studio Audio mode with crystal clear sound.")
    async def hifi(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        await player.apply_filter_preset(FilterPreset.HIFI)
        await interaction.response.send_message(
            embed=create_success_embed("✨ Hi-Fi Studio Mode", "Enabled High-Fidelity Studio Master equalizer for crystal-clear sound.")
        )
        await player.refresh_controller()

    @filter_group.command(name="bassboost", description="Apply bass boost effect to audio.")
    @app_commands.describe(level="Intensity level of bass boost")
    @app_commands.choices(
        level=[
            app_commands.Choice(name="Low Bass", value="bassboost_low"),
            app_commands.Choice(name="Medium Bass", value="bassboost_med"),
            app_commands.Choice(name="High / Heavy Bass", value="bassboost_high"),
        ]
    )
    async def bassboost(self, interaction: discord.Interaction, level: app_commands.Choice[str]) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        preset = FilterPreset(level.value)
        await player.apply_filter_preset(preset)
        await interaction.response.send_message(
            embed=create_success_embed("Bass Boost Applied", f"Active equalizer set to **{level.name}**.")
        )
        await player.refresh_controller()

    @filter_group.command(name="nightcore", description="Speed up audio with higher pitch (Nightcore style).")
    async def nightcore(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        await player.apply_filter_preset(FilterPreset.NIGHTCORE)
        await interaction.response.send_message(
            embed=create_success_embed("Nightcore Mode", "Applied Nightcore timescale filter (1.3x speed & pitch).")
        )
        await player.refresh_controller()

    @filter_group.command(name="vaporwave", description="Slow down audio with deeper pitch (Vaporwave style).")
    async def vaporwave(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        await player.apply_filter_preset(FilterPreset.VAPORWAVE)
        await interaction.response.send_message(
            embed=create_success_embed("Vaporwave Mode", "Applied Vaporwave timescale filter (0.85x speed).")
        )
        await player.refresh_controller()

    @filter_group.command(name="8d", description="Apply rotating 8D binaural headphone audio effect.")
    async def rotation(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        await player.apply_filter_preset(FilterPreset.ROTATION_8D)
        await interaction.response.send_message(
            embed=create_success_embed("8D Audio Mode", "Applied 8D stereo rotation filter.")
        )
        await player.refresh_controller()

    @filter_group.command(name="karaoke", description="Attenuate vocal frequencies for karaoke.")
    async def karaoke(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        await player.apply_filter_preset(FilterPreset.KARAOKE)
        await interaction.response.send_message(
            embed=create_success_embed("Karaoke Mode", "Applied karaoke vocal suppression filter.")
        )
        await player.refresh_controller()

    @filter_group.command(name="clear", description="Remove all active audio filters and reset to flat.")
    async def clear(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        await player.apply_filter_preset(FilterPreset.FLAT)
        await interaction.response.send_message(
            embed=create_success_embed("Filters Reset", "Audio filters have been cleared to standard flat profile.")
        )
        await player.refresh_controller()


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(FiltersCog(bot))
