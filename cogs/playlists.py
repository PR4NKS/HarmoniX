"""Custom user playlist management and playback."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from music.player import HarmoniXPlayer
from ui.embeds import create_success_embed, create_error_embed, create_info_embed
from bot.errors import BotNotInVoiceChannel

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class PlaylistsCog(commands.Cog, name="Playlists"):
    """Create, edit, and play personal custom playlists."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    pl_group = app_commands.Group(name="playlist", description="Custom playlist commands")

    @pl_group.command(name="create", description="Create a new custom playlist.")
    @app_commands.describe(name="Playlist name", is_public="Allow other users in the server to play this playlist")
    async def create(self, interaction: discord.Interaction, name: str, is_public: Optional[bool] = False) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            pl_id = await self.bot.db.create_playlist(user_id=interaction.user.id, name=name, is_public=bool(is_public))
            if pl_id:
                await interaction.response.send_message(
                    embed=create_success_embed("Playlist Created", f"Successfully created playlist **{name}**!"),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Duplicate", f"You already have a playlist named **{name}**."),
                    ephemeral=True,
                )

    @pl_group.command(name="delete", description="Delete an existing playlist.")
    @app_commands.describe(name="Name of playlist to delete")
    async def delete(self, interaction: discord.Interaction, name: str) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            deleted = await self.bot.db.delete_playlist(user_id=interaction.user.id, name=name)
            if deleted:
                await interaction.response.send_message(
                    embed=create_success_embed("Playlist Deleted", f"Deleted playlist **{name}**."),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Not Found", f"Playlist **{name}** was not found."),
                    ephemeral=True,
                )

    @pl_group.command(name="add", description="Add a track to your custom playlist.")
    @app_commands.describe(playlist_name="Name of your playlist", query="Song name, link, or leave blank for now playing")
    async def add(self, interaction: discord.Interaction, playlist_name: str, query: Optional[str] = None) -> None:
        await interaction.response.defer(ephemeral=True)

        if not hasattr(self.bot, "db") or not self.bot.db:
            await interaction.followup.send("Database service unavailable.")
            return

        pl = await self.bot.db.get_playlist_by_name(user_id=interaction.user.id, name=playlist_name)
        if not pl:
            await interaction.followup.send(embed=create_error_embed("Not Found", f"Playlist **{playlist_name}** not found."))
            return

        # Check if user owns this playlist
        if pl.user_id != interaction.user.id:
            await interaction.followup.send(embed=create_error_embed("Permission Denied", "You can only edit your own playlists."))
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
            await interaction.followup.send(embed=create_error_embed("No Song", "Please provide a song to add."))
            return

        success = await self.bot.db.add_track_to_playlist(
            playlist_id=pl.id,  # type: ignore
            title=target_title,
            uri=target_uri,
            author=target_author or "Unknown",
            duration=target_duration,
        )

        if success:
            await interaction.followup.send(
                embed=create_success_embed(
                    "Track Added", f"Added **{target_title}** to playlist **{playlist_name}**!"
                )
            )
        else:
            await interaction.followup.send(embed=create_error_embed("Error", "Could not add track."))

    @pl_group.command(name="list", description="List your playlists.")
    async def list_playlists(self, interaction: discord.Interaction) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            playlists = await self.bot.db.get_user_playlists(interaction.user.id)
            if not playlists:
                await interaction.response.send_message(
                    "You don't have any playlists yet. Create one with `/playlist create`!", ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"📁 {interaction.user.display_name}'s Playlists",
                color=self.bot.settings.COLOR_PRIMARY,
            )
            for pl in playlists:
                visibility = "Public" if pl.is_public else "Private"
                tracks = await self.bot.db.get_playlist_tracks(pl.id)  # type: ignore
                embed.add_field(
                    name=f"• {pl.name}",
                    value=f"Tracks: `{len(tracks)}` | Visibility: `{visibility}`",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @pl_group.command(name="play", description="Queue and play an entire playlist.")
    @app_commands.describe(name="Playlist name")
    async def play_playlist(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer()

        if hasattr(self.bot, "db") and self.bot.db:
            pl = await self.bot.db.get_playlist_by_name(user_id=interaction.user.id, name=name)
            if not pl or not pl.tracks:
                await interaction.followup.send(
                    embed=create_error_embed("Empty or Not Found", f"Playlist **{name}** not found or has no songs.")
                )
                return

            player = await self.bot.music.get_or_create_player(interaction, connect=True)
            queued_count = 0

            for t in pl.tracks:
                results = await self.bot.music.resolve_query(t.uri, requester=interaction.user)  # type: ignore
                if results:
                    track = results[0] if isinstance(results, list) else results.tracks[0]
                    await player.queue.put(track)
                    queued_count += 1

            if not player.playing:
                await player.play_next()

            await interaction.followup.send(
                embed=create_success_embed(
                    "Playlist Queued", f"Enqueued **{queued_count}** songs from playlist **{name}**!"
                )
            )


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(PlaylistsCog(bot))
