"""Interaction and command cooldown handlers."""

from discord import app_commands
import discord


def default_cooldown(rate: int = 1, per: float = 3.0) -> app_commands.checks.Cooldown:
    """Standard user cooldown factory for commands."""
    return app_commands.checks.Cooldown(rate, per)


def user_cooldown(rate: int = 1, per: float = 3.0):
    """App command decorator for user rate limiting."""
    return app_commands.checks.cooldown(rate, per, key=lambda i: (i.guild_id, i.user.id))
