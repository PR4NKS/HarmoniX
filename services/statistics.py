"""System and playback metrics collection."""

import os
import platform
import time
from typing import Dict, Any, TYPE_CHECKING
import discord

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class StatisticsService:
    """Collects runtime diagnostics, node health, and bot analytics."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot
        self.start_time = time.time()

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.start_time

    def get_uptime_formatted(self) -> str:
        """Format uptime into days, hours, minutes, seconds."""
        uptime = int(self.uptime_seconds)
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        return f"{hours}h {minutes}m {seconds}s"

    def get_system_stats(self) -> Dict[str, Any]:
        """Fetch general process information."""
        return {
            "python_version": platform.python_version(),
            "discord_version": discord.__version__,
            "platform": platform.system(),
            "guild_count": len(self.bot.guilds),
            "user_count": sum(g.member_count or 0 for g in self.bot.guilds),
            "voice_connections": len(self.bot.voice_clients),
            "uptime": self.get_uptime_formatted(),
        }
