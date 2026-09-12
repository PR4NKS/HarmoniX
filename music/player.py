"""Custom Wavelink Player subclass with queue, UI controls, autoplay, and 24/7 support."""

import asyncio
from typing import Optional, TYPE_CHECKING
import discord
import wavelink
from .queue import HarmoniXQueue, LoopMode
from .track import HarmoniXTrack
from .filters import FilterPreset, apply_preset
from utils.logging import get_logger

if TYPE_CHECKING:
    from bot.client import HarmoniXBot

logger = get_logger(__name__)


class HarmoniXPlayer(wavelink.Player):
    """Production player wrapping Wavelink voice playback with queue and UI bindings."""

    def __init__(self, client: Optional["HarmoniXBot"] = None, channel: Optional[discord.VoiceChannel] = None):
        super().__init__(client=client, channel=channel)
        self.queue = HarmoniXQueue()
        self.text_channel: Optional[discord.abc.Messageable] = None
        self.controller_message: Optional[discord.Message] = None
        self.current_harmoni_track: Optional[HarmoniXTrack] = None
        self.autoplay_enabled: bool = False
        self.mode_247: bool = False
        self.auto_leave_seconds: int = 180
        self.active_preset: FilterPreset = FilterPreset.FLAT
        self._auto_leave_task: Optional[asyncio.Task] = None
        self._play_lock = asyncio.Lock()

    @property
    def bot(self) -> Optional["HarmoniXBot"]:
        return self.client  # type: ignore

    async def play_next(self) -> None:
        """Fetch and start playback for the next track in the queue."""
        async with self._play_lock:
            self.cancel_auto_leave_timer()

            next_track = await self.queue.get()
            if next_track:
                self.current_harmoni_track = next_track
                try:
                    await self.play(next_track.playable, add_history=False)
                except Exception as e:
                    logger.error("Error playing track %s in guild %s: %s", next_track.title, self.guild.id, e)
                    # Skip to next if current fails
                    asyncio.create_task(self.play_next())
                    return

                # Record playback in database asynchronously
                if self.bot and hasattr(self.bot, "db") and self.bot.db:
                    user_id = next_track.requester.id if next_track.requester else 0
                    asyncio.create_task(
                        self.bot.db.record_playback(
                            guild_id=self.guild.id,
                            user_id=user_id,
                            title=next_track.title,
                            uri=next_track.uri,
                            author=next_track.author,
                            duration=next_track.length,
                        )
                    )

                # Send or update player controller panel
                asyncio.create_task(self.refresh_controller())
            else:
                self.current_harmoni_track = None
                await self.stop()

                # Autoplay check
                if self.autoplay_enabled and self.queue.history:
                    last_track = self.queue.history[-1]
                    recommended = await self._fetch_recommendation(last_track)
                    if recommended:
                        await self.queue.put(recommended)
                        await self.play_next()
                        return

                # Send queue finished notification
                if self.text_channel and not self.mode_247:
                    try:
                        from ui.embeds import create_info_embed
                        embed = create_info_embed(
                            title="Queue Concluded",
                            description="All tracks in the queue have been played. Add more with `/play`!",
                        )
                        await self.text_channel.send(embed=embed)
                    except Exception:
                        pass

                # If queue is completely finished and 24/7 is disabled, start auto-leave countdown
                if not self.mode_247:
                    self.start_auto_leave_timer()

    async def _fetch_recommendation(self, seed_track: HarmoniXTrack) -> Optional[HarmoniXTrack]:
        """Look up related tracks for autoplay continuation."""
        query = f"ytmsearch:{seed_track.author} {seed_track.title}"
        try:
            results = await wavelink.Playable.search(query)
            if results:
                for candidate in results:
                    # Pick a track that wasn't just played
                    if candidate.uri != seed_track.uri:
                        return HarmoniXTrack(
                            playable=candidate,
                            requester=None,
                            album=None,
                            source_name="autoplay",
                        )
        except Exception as e:
            logger.debug("Failed to retrieve autoplay recommendation: %s", e)
        return None

    async def refresh_controller(self) -> None:
        """Create or update the interactive Now Playing control embed."""
        if not self.text_channel or not self.current_harmoni_track:
            return

        try:
            from ui.embeds import create_now_playing_embed
            from ui.views import PlayerControlView

            embed = create_now_playing_embed(self)
            view = PlayerControlView(self)

            if self.controller_message:
                try:
                    await self.controller_message.edit(embed=embed, view=view)
                    return
                except (discord.NotFound, discord.HTTPException):
                    self.controller_message = None

            # Send new message if edit not possible
            self.controller_message = await self.text_channel.send(embed=embed, view=view)
        except Exception as e:
            logger.debug("Failed refreshing controller message: %s", e)

    def start_auto_leave_timer(self, delay: Optional[int] = None) -> None:
        """Begin countdown to disconnect when alone or idle."""
        if self.mode_247:
            return

        self.cancel_auto_leave_timer()
        wait_time = delay if delay is not None else self.auto_leave_seconds
        self._auto_leave_task = asyncio.create_task(self._auto_leave_worker(wait_time))

    def cancel_auto_leave_timer(self) -> None:
        """Cancel any running auto-leave countdown."""
        if self._auto_leave_task and not self._auto_leave_task.done():
            self._auto_leave_task.cancel()
        self._auto_leave_task = None

    async def _auto_leave_worker(self, seconds: int) -> None:
        """Coroutine that executes auto-leave after a timeout."""
        try:
            await asyncio.sleep(seconds)
            # Re-check conditions after sleep
            if not self.mode_247 and (self.queue.is_empty and not self.playing):
                if self.text_channel:
                    try:
                        from ui.embeds import create_info_embed
                        embed = create_info_embed(
                            title="Disconnected",
                            description="Left voice channel due to inactivity. See you next time!",
                        )
                        await self.text_channel.send(embed=embed)
                    except Exception:
                        pass
                await self.teardown()
        except asyncio.CancelledError:
            pass

    async def apply_filter_preset(self, preset: FilterPreset) -> None:
        """Apply a filter preset to the player."""
        filters = self.filters
        apply_preset(filters, preset)
        await self.set_filters(filters)
        self.active_preset = preset

    async def teardown(self) -> None:
        """Cleanly tear down the player and disconnect."""
        self.cancel_auto_leave_timer()
        await self.queue.clear()
        self.current_harmoni_track = None

        if self.controller_message:
            try:
                # Disable all components on controller message
                from ui.views import disable_view_components
                await disable_view_components(self.controller_message)
            except Exception:
                pass
            self.controller_message = None

        try:
            await self.disconnect()
        except Exception as e:
            logger.debug("Exception while disconnecting player: %s", e)
