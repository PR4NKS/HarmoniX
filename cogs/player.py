"""Player controller panel and track inspection commands."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from music.player import HarmoniXPlayer
from ui.embeds import create_now_playing_embed, create_error_embed
from ui.views import PlayerControlView
from bot.errors import BotNotInVoiceChannel

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class PlayerCog(commands.Cog, name="Player"):
    """Interactive player controller and metadata inspection."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    @app_commands.command(name="panel", description="Send a persistent interactive player control panel.")
    async def panel(self, interaction: discord.Interaction) -> None:
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client if interaction.guild else None  # type: ignore
        if not player or not player.current_harmoni_track:
            raise BotNotInVoiceChannel()

        embed = create_now_playing_embed(player)
        view = PlayerControlView(player)
        await interaction.response.send_message(embed=embed, view=view)
        player.controller_message = await interaction.original_response()

    @app_commands.command(name="trackinfo", description="Display detailed metadata for the current or specified track.")
    @app_commands.describe(query="Optional search query or URL to inspect")
    async def trackinfo(self, interaction: discord.Interaction, query: Optional[str] = None) -> None:
        await interaction.response.defer()

        target_track = None
        if query:
            results = await self.bot.music.resolve_query(query, requester=interaction.user)  # type: ignore
            if results:
                target_track = results[0] if isinstance(results, list) else results.tracks[0]
        else:
            player: Optional[HarmoniXPlayer] = interaction.guild.voice_client if interaction.guild else None  # type: ignore
            if player and player.current_harmoni_track:
                target_track = player.current_harmoni_track

        if not target_track:
            await interaction.followup.send(
                embed=create_error_embed("No Track Found", "No track is playing and no query was provided.")
            )
            return

        embed = discord.Embed(
            title=f"ℹ️ Track Metadata: {target_track.title}",
            url=target_track.uri if target_track.uri else None,
            color=self.bot.settings.COLOR_PRIMARY,
        )
        if target_track.artwork:
            embed.set_thumbnail(url=target_track.artwork)

        embed.add_field(name="Artist / Author", value=f"`{target_track.author}`", inline=True)
        embed.add_field(name="Duration", value=f"`{target_track.duration_str}`", inline=True)
        embed.add_field(name="Source Platform", value=f"`{target_track.source_name.title()}`", inline=True)
        embed.add_field(name="Album", value=f"`{target_track.album}`", inline=True)
        embed.add_field(name="Requested By", value=target_track.requester_mention, inline=True)

        await interaction.followup.send(embed=embed)


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(PlayerCog(bot))
