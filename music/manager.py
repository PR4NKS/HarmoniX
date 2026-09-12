"""Music manager coordinating player lifecycle, source resolution, and node events."""

import asyncio
from typing import Optional, List, Dict, Union, TYPE_CHECKING
import aiohttp
import discord
import wavelink
from .player import HarmoniXPlayer
from .track import HarmoniXTrack
from .queue import LoopMode
from .sources import (
    BaseAudioSource,
    PlaylistResult,
    YouTubeSource,
    SpotifySource,
    SoundCloudSource,
    AppleMusicSource,
    DirectURLSource,
)
from bot.errors import (
    UserNotInVoiceChannel,
    BotNotInVoiceChannel,
    DifferentVoiceChannel,
    TrackNotFoundError,
    LavalinkUnavailableError,
)
from utils.logging import get_logger

if TYPE_CHECKING:
    from bot.client import HarmoniXBot

logger = get_logger(__name__)


class MusicManager:
    """High-level facade for music operations, sources, and guild players."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot
        self._sources: List[BaseAudioSource] = []
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._setup_sources()

    def _setup_sources(self) -> None:
        """Register audio source adapters in order of priority."""
        self._sources.append(
            SpotifySource(
                client_id=self.bot.settings.SPOTIFY_CLIENT_ID,
                client_secret=self.bot.settings.SPOTIFY_CLIENT_SECRET,
            )
        )
        self._sources.append(AppleMusicSource())
        self._sources.append(SoundCloudSource())
        self._sources.append(DirectURLSource())
        self._sources.append(YouTubeSource(default_search_type=self.bot.settings.DEFAULT_SEARCH_SOURCE))

    async def get_session(self) -> aiohttp.ClientSession:
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def close(self) -> None:
        """Cleanup session and players."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    async def get_or_create_player(
        self,
        interaction: discord.Interaction,
        connect: bool = True,
    ) -> HarmoniXPlayer:
        """Retrieve existing player for guild or connect to user voice channel."""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise UserNotInVoiceChannel("Command can only be run in a server.")

        voice_state = interaction.user.voice
        if not voice_state or not voice_state.channel:
            raise UserNotInVoiceChannel()

        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore

        if player is None:
            if not connect:
                raise BotNotInVoiceChannel()

            # Check bot permissions in voice channel
            perms = voice_state.channel.permissions_for(interaction.guild.me)
            if not perms.connect or not perms.speak:
                raise UserNotInVoiceChannel(f"I lack permissions to connect or speak in {voice_state.channel.mention}.")

            try:
                player = await voice_state.channel.connect(cls=HarmoniXPlayer)  # type: ignore
            except Exception as e:
                logger.error("Failed to connect player to %s: %s", voice_state.channel.name, e)
                raise LavalinkUnavailableError(f"Could not connect to voice channel: {e}")

            # Apply guild settings (volume, 24/7 mode, etc.)
            if hasattr(self.bot, "db") and self.bot.db:
                settings = await self.bot.db.get_guild_settings(interaction.guild.id)
                player.queue.max_size = settings.max_queue
                player.mode_247 = settings.mode_247
                player.auto_leave_seconds = self.bot.settings.AUTO_LEAVE_SECONDS if settings.auto_leave else 86400
                await player.set_volume(settings.default_volume)

        elif player.channel and player.channel.id != voice_state.channel.id:
            # Bot is already connected to another voice channel
            # Allow move if user is alone or has DJ/admin permissions
            from utils.permissions import has_dj_permissions
            dj_role_id = None
            if hasattr(self.bot, "db") and self.bot.db:
                settings = await self.bot.db.get_guild_settings(interaction.guild.id)
                dj_role_id = settings.dj_role_id

            if has_dj_permissions(interaction.user, dj_role_id=dj_role_id):
                await player.move_to(voice_state.channel)
            else:
                raise DifferentVoiceChannel(f"I am active in {player.channel.mention}. Please join that channel.")

        # Update text channel for player responses
        if isinstance(interaction.channel, discord.abc.Messageable):
            player.text_channel = interaction.channel

        return player

    async def resolve_query(
        self,
        query: str,
        requester: Optional[discord.Member] = None,
        max_results: int = 10,
    ) -> Union[List[HarmoniXTrack], PlaylistResult]:
        """Dispatch query resolution to appropriate source adapter."""
        clean_query = query.strip()
        for source in self._sources:
            if source.can_handle(clean_query):
                try:
                    result = await source.resolve(clean_query, requester=requester, max_results=max_results)
                    if result:
                        return result
                except Exception as e:
                    logger.error("Source adapter %s encountered error: %s", source.name, e)

        # Fallback to default YouTube source
        try:
            return await self._sources[-1].resolve(clean_query, requester=requester, max_results=max_results)
        except Exception as e:
            logger.error("Fallback source failed: %s", e)

        return []
