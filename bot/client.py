"""HarmoniX Discord Bot client implementation."""

import asyncio
import os
from pathlib import Path
from typing import Optional, List
import discord
from discord.ext import commands
import wavelink

from config.settings import Settings, get_settings
from database.connection import DatabaseManager
from database.repository import MusicRepository
from music.manager import MusicManager
from services.lyrics import LyricsService
from services.statistics import StatisticsService
from services.stream_server import StreamServer
from utils.logging import get_logger

logger = get_logger(__name__)


class HarmoniXBot(commands.Bot):
    """Production Discord Music Bot with Wavelink 3.x and SQLite storage."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        intents.message_content = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(self.settings.DEFAULT_PREFIX),
            intents=intents,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=self.settings.BOT_ACTIVITY,
            ),
            status=discord.Status.online,
        )

        # Core Services and Components
        self.db_manager = DatabaseManager(self.settings.DATABASE_PATH)
        self.db = MusicRepository(self.db_manager)
        self.music = MusicManager(self)
        self.lyrics = LyricsService(genius_token=self.settings.GENIUS_API_TOKEN)
        self.stats = StatisticsService(self)
        self.stream_server = StreamServer(
            host="0.0.0.0",
            port=self.settings.STREAM_PROXY_PORT,
            callback_host=self.settings.STREAM_PROXY_HOST,
        )

    async def setup_hook(self) -> None:
        """Asynchronous initialization before gateway login."""
        logger.info("Initializing HarmoniX core infrastructure...")

        # 0. Start local audio stream proxy
        try:
            await self.stream_server.start()
        except Exception as e:
            logger.warning("Could not start audio stream proxy: %s", e)

        # 1. Connect Database
        await self.db_manager.connect()

        # 2. Connect Lavalink Audio Node
        node = wavelink.Node(
            uri=self.settings.LAVALINK_URI,
            password=self.settings.LAVALINK_PASSWORD,
            inactive_player_timeout=300,
        )
        try:
            await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
            logger.info("Connected Lavalink pool to %s", self.settings.LAVALINK_URI)
        except Exception as e:
            logger.warning("Could not establish immediate Lavalink connection: %s (Will retry in background)", e)

        # 3. Dynamically load all cogs
        cogs_dir = Path(__file__).parent.parent / "cogs"
        loaded_cogs: List[str] = []
        for file in cogs_dir.glob("*.py"):
            if not file.name.startswith("__"):
                cog_name = f"cogs.{file.stem}"
                try:
                    await self.load_extension(cog_name)
                    loaded_cogs.append(file.stem)
                except Exception as e:
                    logger.error("Failed to load cog extension %s: %s", cog_name, e)

        logger.info("Successfully loaded %d cogs: %s", len(loaded_cogs), ", ".join(loaded_cogs))

        # 4. Attach error handlers and event listeners
        from bot.events import setup_events
        setup_events(self)

        # 5. Sync Slash Commands Tree
        try:
            synced = await self.tree.sync()
            logger.info("Synced %d global application slash commands.", len(synced))
        except Exception as e:
            logger.error("Failed to sync slash commands: %s", e)

    async def close(self) -> None:
        """Graceful shutdown sequence."""
        logger.info("Initiating graceful shutdown for HarmoniX...")

        # Disconnect all active guild players
        for vc in list(self.voice_clients):
            try:
                if hasattr(vc, "teardown"):
                    await vc.teardown()
                else:
                    await vc.disconnect()
            except Exception as e:
                logger.debug("Error disconnecting player on close: %s", e)

        # Close sessions, stream server and database
        try:
            await self.stream_server.stop()
        except Exception:
            pass
        await self.music.close()
        await self.lyrics.close()
        await self.db_manager.close()

        await super().close()
        logger.info("HarmoniX shutdown complete.")
