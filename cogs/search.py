"""Interactive search command with dropdown menu selection."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from music.player import HarmoniXPlayer
from music.sources import PlaylistResult
from ui.views import SearchSelectView
from ui.embeds import create_error_embed
from utils.permissions import check_voice_state

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class SearchCog(commands.Cog, name="Search"):
    """Interactive multi-result search."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    @app_commands.command(name="search", description="Search for songs and choose which one to play via a dropdown.")
    @app_commands.describe(query="Song title or query to search")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        """Search query and return an interactive dropdown selection."""
        await interaction.response.defer()

        # Connect or fetch player
        player = await self.bot.music.get_or_create_player(interaction, connect=True)

        # Resolve query with max_results=10
        results = await self.bot.music.resolve_query(query, requester=interaction.user, max_results=10)  # type: ignore

        if not results:
            await interaction.followup.send(
                embed=create_error_embed("No Results", f"Could not find any songs matching `{query}`.")
            )
            return

        tracks = results.tracks if isinstance(results, PlaylistResult) else results

        # Create search embed
        embed = discord.Embed(
            title=f"🔍 Search Results for: {query[:60]}",
            description="Select a song from the dropdown menu below to enqueue it.",
            color=self.bot.settings.COLOR_PRIMARY,
        )

        for i, t in enumerate(tracks[:10], start=1):
            embed.add_field(
                name=f"{i}. {t.title[:65]}",
                value=f"Artist: **{t.author[:40]}** | Duration: `{t.duration_str}`",
                inline=False,
            )

        if tracks[0].artwork:
            embed.set_thumbnail(url=tracks[0].artwork)

        view = SearchSelectView(tracks=tracks, requester=interaction.user, player=player)  # type: ignore
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(SearchCog(bot))
