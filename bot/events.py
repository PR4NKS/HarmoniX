"""Event listeners, Wavelink lifecycle hooks, voice state handlers, and error dispatchers."""

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import wavelink

from bot.errors import MusicBotException
from music.player import HarmoniXPlayer
from ui.embeds import create_error_embed, create_info_embed
from utils.logging import get_logger

logger = get_logger(__name__)


def setup_events(bot: "HarmoniXBot") -> None:  # type: ignore
    """Register all event listeners onto the bot instance."""

    @bot.event
    async def on_ready():
        logger.info(
            "HarmoniX is online! Logged in as %s (ID: %s) serving %d guilds.",
            bot.user,
            bot.user.id,
            len(bot.guilds),
        )

    @bot.event
    async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload) -> None:
        logger.info("Lavalink audio node is online and ready: %s (Resumed: %s)", payload.node.identifier, payload.resumed)

    @bot.event
    async def on_wavelink_node_disconnected(payload: wavelink.NodeDisconnectedEventPayload) -> None:
        logger.warning("Lavalink node %s disconnected.", payload.node.identifier)

    @bot.event
    async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload) -> None:
        """Fires when a track completes, fails, or is stopped."""
        player: HarmoniXPlayer = payload.player  # type: ignore
        if not player:
            return

        reason = payload.reason
        logger.debug("Track ended: %s (Reason: %s) in guild %s", payload.track.title, reason, player.guild.id)

        # Do not automatically advance if the track was explicitly replaced by a new track play
        if reason in ("replaced",):
            return

        # Advance queue
        await player.play_next()

    @bot.event
    async def on_wavelink_track_exception(payload: wavelink.TrackExceptionEventPayload) -> None:
        """Handle playback exceptions reported from Lavalink with automatic fallback."""
        player: HarmoniXPlayer = payload.player  # type: ignore
        if not player:
            return

        source = str(getattr(payload.track, "source", "unknown")).lower()
        title = getattr(payload.track, "title", "Unknown Track")
        author = getattr(payload.track, "author", "")
        logger.warning("Audio playback error for %s (source: %s): %s", title, source, payload.exception)

        # If YouTube / YouTube Music blocks the stream, automatically fallback to SoundCloud
        if "youtube" in source or source in ("unknown", "http", ""):
            try:
                import re
                clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title)
                clean_title = re.sub(r'\s*-\s*Topic', '', clean_title, flags=re.IGNORECASE).strip()
                clean_author = re.sub(r'\s*-\s*Topic', '', author, flags=re.IGNORECASE).strip()

                queries_to_try = []
                if clean_title and clean_author and clean_author.lower() not in clean_title.lower():
                    queries_to_try.append(f"{clean_title} {clean_author}")
                if clean_title:
                    queries_to_try.append(clean_title)
                queries_to_try.append(title)

                fallback_results = None
                for q in queries_to_try:
                    try:
                        logger.info("Attempting automatic SoundCloud stream fallback for: '%s'", q)
                        fallback_results = await wavelink.Playable.search(q, source=wavelink.TrackSource.SoundCloud)
                        if fallback_results:
                            break
                    except Exception as search_err:
                        logger.debug("Fallback search '%s' failed: %s", q, search_err)
                        continue

                if fallback_results:
                    target_track = fallback_results[0]
                    from music.track import HarmoniXTrack
                    player.current_harmoni_track = HarmoniXTrack(
                        playable=target_track,
                        requester=player.current_harmoni_track.requester if player.current_harmoni_track else None,
                        album="SoundCloud Fallback",
                        source_name="soundcloud",
                    )
                    await player.play(target_track, add_history=False)
                    asyncio.create_task(player.refresh_controller())

                    if player.text_channel:
                        try:
                            embed = create_success_embed(
                                "Playback Recovered",
                                f"Recovered stream for **{target_track.title}** via SoundCloud.",
                            )
                            await player.text_channel.send(embed=embed)
                        except Exception:
                            pass
                    return
            except Exception as fb_err:
                logger.error("SoundCloud fallback failed: %s", fb_err)

        if player.text_channel:
            try:
                embed = create_error_embed(
                    "Playback Failed",
                    f"An error occurred while streaming **{title}**. Skipping to next track...",
                )
                await player.text_channel.send(embed=embed)
            except Exception:
                pass

        await player.play_next()

    @bot.event
    async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Monitor voice channel activity for auto-leave behavior."""
        # Check if the bot was disconnected externally (e.g. kicked or moved)
        if member.id == bot.user.id:
            if before.channel and not after.channel:
                # Bot was disconnected from voice
                player: HarmoniXPlayer = member.guild.voice_client  # type: ignore
                if player:
                    await player.teardown()
            return

        # Check if users left the bot's voice channel
        guild = member.guild
        player: HarmoniXPlayer = guild.voice_client  # type: ignore
        if not player or not player.channel:
            return

        # Check if this update involves the bot's voice channel
        bot_vc = player.channel
        if before.channel == bot_vc or after.channel == bot_vc:
            non_bot_members = [m for m in bot_vc.members if not m.bot]

            if len(non_bot_members) == 0:
                # Bot is alone in the voice channel
                if not player.mode_247:
                    logger.info("Bot is alone in VC in guild %s. Starting auto-leave timer.", guild.id)
                    player.start_auto_leave_timer(player.auto_leave_seconds)
            else:
                # At least one listener is present, cancel any leave timer
                player.cancel_auto_leave_timer()

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """Unified slash command error handler."""
        # Unwrap invoke errors
        original_error = getattr(error, "original", error)

        if isinstance(original_error, MusicBotException):
            embed = create_error_embed("Music Error", original_error.message)
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if isinstance(error, app_commands.CommandOnCooldown):
            embed = create_error_embed(
                "Cooldown Active",
                f"Please wait `{error.retry_after:.1f}s` before using this command again.",
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if isinstance(error, app_commands.MissingPermissions):
            embed = create_error_embed(
                "Missing Permissions",
                f"You lack the required server permissions: {', '.join(error.missing_permissions)}",
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Unexpected unhandled exceptions
        logger.exception("Unhandled application command exception: %s", original_error)
        embed = create_error_embed(
            "Unexpected Error",
            "An unexpected error occurred while executing this command. Please try again later.",
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            pass
