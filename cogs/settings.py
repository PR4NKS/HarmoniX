"""Guild configuration and settings management."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from ui.embeds import create_success_embed, create_info_embed

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class SettingsCog(commands.Cog, name="Settings"):
    """Server-specific configuration for DJ roles, volume, and timeouts."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    settings_group = app_commands.Group(
        name="settings",
        description="Configure server music options",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @settings_group.command(name="view", description="View current server music settings.")
    async def view(self, interaction: discord.Interaction) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            cfg = await self.bot.db.get_guild_settings(interaction.guild.id)  # type: ignore

            dj_role = interaction.guild.get_role(cfg.dj_role_id) if cfg.dj_role_id else None  # type: ignore
            dj_str = dj_role.mention if dj_role else "None (Anyone alone or with 'DJ' role)"

            embed = discord.Embed(
                title=f"⚙️ Music Configuration for {interaction.guild.name}",  # type: ignore
                color=self.bot.settings.COLOR_PRIMARY,
            )
            embed.add_field(name="DJ Role", value=dj_str, inline=True)
            embed.add_field(name="Default Volume", value=f"`{cfg.default_volume}%`", inline=True)
            embed.add_field(name="Max Queue Size", value=f"`{cfg.max_queue}` tracks", inline=True)
            embed.add_field(name="Auto Leave", value=f"`{'Enabled' if cfg.auto_leave else 'Disabled'}`", inline=True)
            embed.add_field(name="24/7 Mode", value=f"`{'Active' if cfg.mode_247 else 'Disabled'}`", inline=True)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Database service unavailable.", ephemeral=True)

    @settings_group.command(name="dj-role", description="Set the DJ role for this server.")
    @app_commands.describe(role="The role required for DJ controls")
    async def set_dj_role(self, interaction: discord.Interaction, role: Optional[discord.Role] = None) -> None:
        role_id = role.id if role else None
        if hasattr(self.bot, "db") and self.bot.db:
            await self.bot.db.update_guild_settings(interaction.guild.id, dj_role_id=role_id)  # type: ignore
            status = role.mention if role else "None (Cleared)"
            await interaction.response.send_message(
                embed=create_success_embed("DJ Role Updated", f"DJ role is now set to {status}.")
            )

    @settings_group.command(name="default-volume", description="Set default initial volume for new players.")
    @app_commands.describe(volume="Volume percentage (0 - 100)")
    async def set_default_volume(self, interaction: discord.Interaction, volume: app_commands.Range[int, 0, 100]) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            await self.bot.db.update_guild_settings(interaction.guild.id, default_volume=volume)  # type: ignore
            await interaction.response.send_message(
                embed=create_success_embed("Volume Configured", f"Default volume set to **{volume}%**.")
            )

    @settings_group.command(name="max-queue", description="Configure the maximum allowed tracks in queue.")
    @app_commands.describe(limit="Maximum queue limit (10 - 2000)")
    async def set_max_queue(self, interaction: discord.Interaction, limit: app_commands.Range[int, 10, 2000]) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            await self.bot.db.update_guild_settings(interaction.guild.id, max_queue=limit)  # type: ignore
            await interaction.response.send_message(
                embed=create_success_embed("Queue Limit Updated", f"Maximum queue capacity set to **{limit}** tracks.")
            )

    @settings_group.command(name="auto-leave", description="Toggle whether the bot leaves voice when alone or idle.")
    @app_commands.describe(enabled="Enable or disable auto-disconnect")
    async def set_auto_leave(self, interaction: discord.Interaction, enabled: bool) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            await self.bot.db.update_guild_settings(interaction.guild.id, auto_leave=enabled)  # type: ignore
            status = "enabled" if enabled else "disabled"
            await interaction.response.send_message(
                embed=create_success_embed("Auto-Leave Updated", f"Inactivity auto-leave is now **{status}**.")
            )

    @settings_group.command(name="reset", description="Reset all server settings to defaults.")
    async def reset(self, interaction: discord.Interaction) -> None:
        if hasattr(self.bot, "db") and self.bot.db:
            await self.bot.db.reset_guild_settings(interaction.guild.id)  # type: ignore
            await interaction.response.send_message(
                embed=create_success_embed("Settings Reset", "Server configuration restored to defaults.")
            )


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(SettingsCog(bot))
