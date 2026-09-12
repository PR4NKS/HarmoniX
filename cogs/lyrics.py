"""Song lyrics command with pagination and synchronization support."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from music.player import HarmoniXPlayer
from ui.embeds import create_lyrics_embed, create_error_embed
from ui.views import LyricsPaginationView

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class LyricsCog(commands.Cog, name="Lyrics"):
    """Fetch and display song lyrics."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    @app_commands.command(name="lyrics", description="Fetch song lyrics for the current song or a specific search.")
    @app_commands.describe(query="Optional song name and artist to search")
    async def lyrics(self, interaction: discord.Interaction, query: Optional[str] = None) -> None:
        await interaction.response.defer()

        search_title: Optional[str] = None
        search_artist: Optional[str] = None
        duration_s: Optional[int] = None

        if query:
            search_title = query
        else:
            player: Optional[HarmoniXPlayer] = interaction.guild.voice_client if interaction.guild else None  # type: ignore
            if player and player.current_harmoni_track:
                search_title = player.current_harmoni_track.title
                search_artist = player.current_harmoni_track.author
                duration_s = int(player.current_harmoni_track.length // 1000)

        if not search_title:
            await interaction.followup.send(
                embed=create_error_embed(
                    "No Song Specified",
                    "No song is currently playing. Please provide a query (e.g. `/lyrics Bohemian Rhapsody`).",
                )
            )
            return

        # Fetch lyrics from service
        data = await self.bot.lyrics.get_lyrics(title=search_title, artist=search_artist, duration_seconds=duration_s)

        if not data or not (data.get("plain_lyrics") or data.get("synced_lyrics")):
            await interaction.followup.send(
                embed=create_error_embed("Lyrics Not Found", f"Could not find lyrics for **{search_title}**.")
            )
            return

        lyrics_text = data.get("plain_lyrics") or data.get("synced_lyrics", "")
        pages = self.bot.lyrics.paginate_lyrics(lyrics_text, max_chars=1200)

        embed = create_lyrics_embed(
            title=data["title"],
            artist=data["artist"],
            lyrics_page=pages[0],
            current_page=1,
            total_pages=len(pages),
        )

        if len(pages) > 1:
            view = LyricsPaginationView(title=data["title"], artist=data["artist"], pages=pages)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(LyricsCog(bot))
