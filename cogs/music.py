"""Core playback commands: play, pause, resume, skip, stop, volume, seek, nowplaying, 24/7."""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, TYPE_CHECKING

from music.player import HarmoniXPlayer
from music.sources import PlaylistResult
from utils.permissions import require_voice, check_voice_state, has_dj_permissions
from utils.validators import parse_time_to_seconds, format_duration
from ui.embeds import (
    create_track_queued_embed,
    create_playlist_queued_embed,
    create_now_playing_embed,
    create_success_embed,
    create_error_embed,
    create_info_embed,
)
from bot.errors import (
    UserNotInVoiceChannel,
    DifferentVoiceChannel,
    BotNotInVoiceChannel,
    TrackNotFoundError,
    DJRoleRequiredError,
)

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class MusicCog(commands.Cog, name="Music"):
    """Core audio playback and voice channel management commands."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    @app_commands.command(name="play", description="Play a song, playlist, or stream from YouTube, Spotify, etc.")
    @app_commands.describe(query="Song title, artist, or URL (YouTube, Spotify, SoundCloud, etc.)")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        """Enqueue or immediately play audio from a query or URL."""
        await interaction.response.defer()

        # Connect or fetch player
        player = await self.bot.music.get_or_create_player(interaction, connect=True)

        # Resolve query through registered sources
        result = await self.bot.music.resolve_query(query, requester=interaction.user)  # type: ignore

        if not result:
            await interaction.followup.send(
                embed=create_error_embed("Not Found", f"Could not find any playable audio for `{query}`.")
            )
            return

        is_playing = player.playing

        if isinstance(result, PlaylistResult):
            added_count = await player.queue.put_tracks(result.tracks)
            if not is_playing:
                await player.play_next()

            thumbnail = result.tracks[0].artwork if result.tracks else None
            embed = create_playlist_queued_embed(
                playlist_name=result.name,
                track_count=added_count,
                requester=interaction.user,  # type: ignore
                thumbnail_url=thumbnail,
            )
            await interaction.followup.send(embed=embed)

        else:
            # Single track or list of results
            track = result[0]
            await player.queue.put(track)

            if not is_playing:
                await player.play_next()
                embed = create_success_embed("Now Playing", f"Playing [{track.title}]({track.uri})!")
                await interaction.followup.send(embed=embed)
            else:
                pos = len(player.queue)
                embed = create_track_queued_embed(track, position=pos)
                await interaction.followup.send(embed=embed)

    @app_commands.command(name="join", description="Connect HarmoniX to your current voice channel.")
    async def join(self, interaction: discord.Interaction) -> None:
        """Explicitly connect the bot to the voice channel."""
        player = await self.bot.music.get_or_create_player(interaction, connect=True)
        await interaction.response.send_message(
            embed=create_success_embed("Connected", f"Joined {player.channel.mention}.")
        )

    @app_commands.command(name="leave", description="Disconnect HarmoniX from the voice channel.")
    async def leave(self, interaction: discord.Interaction) -> None:
        """Disconnect the bot from voice."""
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if player:
            await player.teardown()
            await interaction.response.send_message(
                embed=create_info_embed("Disconnected", "Left the voice channel and cleared queue.")
            )
        else:
            raise BotNotInVoiceChannel()

    @app_commands.command(name="pause", description="Pause the currently playing track.")
    async def pause(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player or not player.playing:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)
            return

        await player.pause(True)
        await interaction.response.send_message(embed=create_success_embed("Paused", "Audio playback has been paused."))
        await player.refresh_controller()

    @app_commands.command(name="resume", description="Resume paused audio playback.")
    async def resume(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player or not player.paused:
            await interaction.response.send_message("Audio is not currently paused.", ephemeral=True)
            return

        await player.pause(False)
        await interaction.response.send_message(embed=create_success_embed("Resumed", "Audio playback has resumed."))
        await player.refresh_controller()

    @app_commands.command(name="skip", description="Skip to the next song in the queue.")
    async def skip(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player or not player.current_harmoni_track:
            await interaction.response.send_message("Nothing is currently playing to skip.", ephemeral=True)
            return

        skipped_title = player.current_harmoni_track.title
        await interaction.response.send_message(
            embed=create_success_embed("Skipped", f"Skipped **{skipped_title}**.")
        )
        await player.play_next()

    @app_commands.command(name="previous", description="Replay the previous track from history.")
    async def previous(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player:
            raise BotNotInVoiceChannel()

        prev = await player.queue.get_previous()
        if prev:
            await interaction.response.send_message(
                embed=create_success_embed("Replaying", f"Playing previous track: **{prev.title}**.")
            )
            await player.play_next()
        else:
            await interaction.response.send_message("No previous tracks found in history.", ephemeral=True)

    @app_commands.command(name="replay", description="Restart the current track from the beginning.")
    async def replay(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player or not player.current_harmoni_track:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)
            return

        await player.seek(0)
        await interaction.response.send_message(
            embed=create_success_embed("Restarted", f"Restarted **{player.current_harmoni_track.title}**.")
        )
        await player.refresh_controller()

    @app_commands.command(name="stop", description="Stop music playback and clear the queue.")
    async def stop(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player:
            raise BotNotInVoiceChannel()

        await player.teardown()
        await interaction.response.send_message(
            embed=create_success_embed("Stopped", "Playback stopped, queue cleared, and player disconnected.")
        )

    @app_commands.command(name="volume", description="Set playback volume (0 to 100).")
    @app_commands.describe(level="Volume percentage between 0 and 100")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 100]) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player:
            raise BotNotInVoiceChannel()

        await player.set_volume(level)
        await interaction.response.send_message(
            embed=create_success_embed("Volume Changed", f"Volume set to **{level}%**.")
        )
        await player.refresh_controller()

    @app_commands.command(name="seek", description="Jump to a specific timestamp in the current song.")
    @app_commands.describe(timestamp="Position to seek (e.g. 1:30 or 90s)")
    async def seek(self, interaction: discord.Interaction, timestamp: str) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player or not player.current_harmoni_track:
            await interaction.response.send_message("No track is currently playing.", ephemeral=True)
            return

        seconds = parse_time_to_seconds(timestamp)
        if seconds is None:
            await interaction.response.send_message("Invalid timestamp format. Use `mm:ss` or `hh:mm:ss`.", ephemeral=True)
            return

        target_ms = seconds * 1000
        if target_ms > player.current_harmoni_track.length:
            await interaction.response.send_message("Cannot seek past the end of the song.", ephemeral=True)
            return

        await player.seek(target_ms)
        await interaction.response.send_message(
            embed=create_success_embed("Seek Complete", f"Seeked to **{format_duration(target_ms)}**.")
        )
        await player.refresh_controller()

    @app_commands.command(name="nowplaying", description="Display the interactive Now Playing control panel.")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        from ui.views import PlayerControlView
        embed = create_now_playing_embed(player)
        view = PlayerControlView(player)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="autoplay", description="Toggle automatic playback of related music when queue ends.")
    async def autoplay(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if not player:
            raise BotNotInVoiceChannel()

        player.autoplay_enabled = not player.autoplay_enabled
        status = "enabled" if player.autoplay_enabled else "disabled"
        await interaction.response.send_message(
            embed=create_success_embed("Autoplay Updated", f"Autoplay is now **{status}**.")
        )

    @app_commands.command(name="247", description="Toggle 24/7 mode to keep HarmoniX connected continuously.")
    async def mode_247(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)

        if not has_dj_permissions(interaction.user):  # type: ignore
            raise DJRoleRequiredError()

        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        player.mode_247 = not player.mode_247
        if player.mode_247:
            player.cancel_auto_leave_timer()

        # Persist in DB
        if hasattr(self.bot, "db") and self.bot.db:
            await self.bot.db.update_guild_settings(interaction.guild.id, mode_247=player.mode_247)

        status = "enabled" if player.mode_247 else "disabled"
        await interaction.response.send_message(
            embed=create_success_embed("24/7 Mode Updated", f"24/7 voice presence is now **{status}**.")
        )


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(MusicCog(bot))
