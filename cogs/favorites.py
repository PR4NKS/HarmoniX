"""User favorite tracks system backed by async SQLite repository."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from music.player import HarmoniXPlayer
from ui.embeds import create_success_embed, create_error_embed, create_info_embed
from bot.errors import BotNotInVoiceChannel

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class FavoritesCog(commands.Cog, name="Favorites"):
    """Manage and listen to your personal favorite tracks."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    fav_group = app_commands.Group(name="favorite", description="Personal favorites commands")

    @fav_group.command(name="add", description="Add the currently playing track (or search) to your favorites.")
    @app_commands.describe(query="Optional song name or URL to add instead of currently playing")
    async def add(self, interaction: discord.Interaction, query: Optional[str] = None) -> None:
        if not hasattr(self.bot, "db") or not self.bot.db:
            await interaction.response.send_message("Database is currently unavailable.", ephemeral=True)
            return

        target_title = None
        target_uri = None
        target_author = None
        target_duration = 0

        if query:
            results = await self.bot.music.resolve_query(query, requester=interaction.user)  # type: ignore
            if results:
                t = results[0] if isinstance(results, list) else results.tracks[0]
                target_title, target_uri, target_author, target_duration = t.title, t.uri, t.author, t.length
        else:
            player: Optional[HarmoniXPlayer] = interaction.guild.voice_client if interaction.guild else None  # type: ignore
            if player and player.current_harmoni_track:
                t = player.current_harmoni_track
                target_title, target_uri, target_author, target_duration = t.title, t.uri, t.author, t.length

        if not target_title or not target_uri:
            await interaction.response.send_message(
                embed=create_error_embed("No Song Found", "Play a song first or specify a query to add."),
                ephemeral=True,
            )
            return

        added = await self.bot.db.add_favorite(
            user_id=interaction.user.id,
            title=target_title,
            uri=target_uri,
            author=target_author or "Unknown",
            duration=target_duration,
        )

        if added:
            await interaction.response.send_message(
                embed=create_success_embed("Added to Favorites", f"Saved **{target_title}** to your favorites!"),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=create_info_embed("Already in Favorites", f"**{target_title}** is already in your favorites."),
                ephemeral=True,
            )

    @fav_group.command(name="remove", description="Remove a track from your favorites.")
    @app_commands.describe(title_or_uri="Song title or URL to remove")
    async def remove(self, interaction: discord.Interaction, title_or_uri: str) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            removed = await self.bot.db.remove_favorite(interaction.user.id, title_or_uri)
            if removed:
                await interaction.response.send_message(
                    embed=create_success_embed("Removed", f"Removed **{title_or_uri}** from your favorites."),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Not Found", f"Could not find `{title_or_uri}` in your favorites."),
                    ephemeral=True,
                )

    @fav_group.command(name="list", description="View all your saved favorite tracks.")
    async def list_favorites(self, interaction: discord.Interaction) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            favs = await self.bot.db.get_favorites(interaction.user.id)
            if not favs:
                await interaction.response.send_message("You don't have any saved favorites yet. Use `/favorite add`!", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"⭐ {interaction.user.display_name}'s Favorite Tracks",
                color=self.bot.settings.COLOR_PRIMARY,
            )
            lines = []
            for i, f in enumerate(favs[:20], start=1):
                lines.append(f"`{i:2d}.` [{f.title}]({f.uri}) • `{f.author}`")
            embed.description = "\n".join(lines)
            embed.set_footer(text=f"Total: {len(favs)} favorites")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @fav_group.command(name="play", description="Queue all your saved favorite tracks.")
    async def play_favorites(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if hasattr(self.bot, "db") and self.bot.db:
            favs = await self.bot.db.get_favorites(interaction.user.id)
            if not favs:
                await interaction.followup.send(embed=create_error_embed("No Favorites", "You haven't saved any favorites yet."))
                return

            player = await self.bot.music.get_or_create_player(interaction, connect=True)
            queued_count = 0

            for fav in favs:
                results = await self.bot.music.resolve_query(fav.uri, requester=interaction.user)  # type: ignore
                if results:
                    track = results[0] if isinstance(results, list) else results.tracks[0]
                    await player.queue.put(track)
                    queued_count += 1

            if not player.playing:
                await player.play_next()

            await interaction.followup.send(
                embed=create_success_embed(
                    "Playing Favorites", f"Enqueued **{queued_count}** songs from your favorites collection!"
                )
            )


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(FavoritesCog(bot))
