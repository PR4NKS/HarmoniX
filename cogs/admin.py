"""System diagnostics, node status, and administrative commands."""

import os
import platform
import time
from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands
import wavelink

from ui.embeds import create_success_embed, create_info_embed, create_error_embed

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class AdminCog(commands.Cog, name="Admin"):
    """System diagnostics, status checks, and owner utilities."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    @app_commands.command(name="ping", description="Check Discord API and Lavalink audio latency.")
    async def ping(self, interaction: discord.Interaction) -> None:
        gateway_ms = round(self.bot.latency * 1000)

        # Measure Lavalink node ping if active
        node_ping_str = "N/A"
        try:
            node = wavelink.Pool.get_node()
            if node and hasattr(node, "ping"):
                node_ping_str = f"{round(node.ping)}ms"
        except Exception:
            pass

        embed = discord.Embed(
            title="🏓 Pong!",
            color=self.bot.settings.COLOR_PRIMARY,
        )
        embed.add_field(name="Gateway Latency", value=f"`{gateway_ms}ms`", inline=True)
        embed.add_field(name="Audio Node Latency", value=f"`{node_ping_str}`", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="status", description="Display live system health, Lavalink nodes, and bot statistics.")
    async def status(self, interaction: discord.Interaction) -> None:
        stats = self.bot.stats.get_system_stats()

        # Node status
        node_lines = []
        try:
            nodes = wavelink.Pool.nodes
            for identifier, node in nodes.items():
                status_icon = "🟢" if node.status == wavelink.NodeStatus.CONNECTED else "🔴"
                node_lines.append(f"{status_icon} **{identifier}**: `{node.status.name}`")
        except Exception:
            node_lines.append("No active nodes.")

        embed = discord.Embed(
            title=f"⚡ {self.bot.settings.BOT_NAME} System Health",
            color=self.bot.settings.COLOR_PRIMARY,
        )
        embed.add_field(name="Uptime", value=f"`{stats['uptime']}`", inline=True)
        embed.add_field(name="Guilds", value=f"`{stats['guild_count']}`", inline=True)
        embed.add_field(name="Active Players", value=f"`{stats['voice_connections']}`", inline=True)

        embed.add_field(name="Discord.py", value=f"`v{stats['discord_version']}`", inline=True)
        embed.add_field(name="Python", value=f"`v{stats['python_version']}`", inline=True)
        embed.add_field(name="OS", value=f"`{stats['platform']}`", inline=True)

        embed.add_field(name="Lavalink Audio Nodes", value="\n".join(node_lines) or "None", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reload", description="Reload a bot extension (Owner Only).")
    @app_commands.describe(extension="Name of the cog extension (e.g. music, queue)")
    async def reload_cog(self, interaction: discord.Interaction, extension: str) -> None:
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("This command is restricted to the bot owner.", ephemeral=True)
            return

        ext_full = f"cogs.{extension}" if not extension.startswith("cogs.") else extension
        try:
            await self.bot.reload_extension(ext_full)
            await interaction.response.send_message(
                embed=create_success_embed("Extension Reloaded", f"Successfully reloaded `{ext_full}`."),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed("Reload Error", f"Failed to reload `{ext_full}`: {e}"),
                ephemeral=True,
            )


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(AdminCog(bot))
