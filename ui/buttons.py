"""Custom button definitions and icons."""

import discord
from discord import ui


class ActionButton(ui.Button):
    """Reusable action button with custom styling."""

    def __init__(self, label: str, style: discord.ButtonStyle = discord.ButtonStyle.secondary, emoji: str = None, custom_id: str = None):
        super().__init__(label=label, style=style, emoji=emoji, custom_id=custom_id)
