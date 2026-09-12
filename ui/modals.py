"""Interactive Discord Modals for user inputs."""

import discord
from discord import ui
from utils.validators import parse_time_to_seconds
from utils.permissions import has_dj_permissions
from ui.embeds import create_success_embed, create_error_embed


class VolumeModal(ui.Modal, title="Adjust Playback Volume"):
    """Modal allowing precise numeric volume entry."""

    volume_input = ui.TextInput(
        label="Volume (0 - 100)",
        placeholder="e.g. 80",
        min_length=1,
        max_length=3,
        required=True,
    )

    def __init__(self, player: "HarmoniXPlayer"):  # type: ignore
        super().__init__()
        self.player = player

    async def on_submit(self, interaction: discord.Interaction) -> None:
        val_str = self.volume_input.value.strip()
        if not val_str.isdigit():
            await interaction.response.send_message(
                embed=create_error_embed("Invalid Input", "Please enter a valid whole number between 0 and 100."),
                ephemeral=True,
            )
            return

        volume = int(val_str)
        if not (0 <= volume <= 100):
            await interaction.response.send_message(
                embed=create_error_embed("Out of Range", "Volume must be between 0 and 100."),
                ephemeral=True,
            )
            return

        await self.player.set_volume(volume)
        await interaction.response.send_message(
            embed=create_success_embed("Volume Updated", f"Playback volume set to **{volume}%**."),
            ephemeral=True,
        )
        await self.player.refresh_controller()


class SeekModal(ui.Modal, title="Seek Track Position"):
    """Modal for jumping to a specific timestamp in the current track."""

    timestamp_input = ui.TextInput(
        label="Timestamp (e.g. 1:30, 02:45, 90s)",
        placeholder="1:30",
        min_length=1,
        max_length=10,
        required=True,
    )

    def __init__(self, player: "HarmoniXPlayer"):  # type: ignore
        super().__init__()
        self.player = player

    async def on_submit(self, interaction: discord.Interaction) -> None:
        seconds = parse_time_to_seconds(self.timestamp_input.value)
        if seconds is None:
            await interaction.response.send_message(
                embed=create_error_embed("Invalid Format", "Use format `1:30` (mm:ss) or `90` (seconds)."),
                ephemeral=True,
            )
            return

        if not self.player.current_harmoni_track:
            await interaction.response.send_message(
                embed=create_error_embed("No Track Playing", "There is no track currently playing to seek."),
                ephemeral=True,
            )
            return

        target_ms = seconds * 1000
        if target_ms > self.player.current_harmoni_track.length:
            await interaction.response.send_message(
                embed=create_error_embed("Out of Range", "Cannot seek past the end of the track."),
                ephemeral=True,
            )
            return

        await self.player.seek(target_ms)
        await interaction.response.send_message(
            embed=create_success_embed("Seek Position", f"Jumped to **{self.timestamp_input.value}**."),
            ephemeral=True,
        )
        await self.player.refresh_controller()


class PlaylistCreateModal(ui.Modal, title="Create Personal Playlist"):
    """Modal for creating a named playlist."""

    name_input = ui.TextInput(
        label="Playlist Name",
        placeholder="My Chill Vibes",
        min_length=2,
        max_length=50,
        required=True,
    )

    def __init__(self, bot: "HarmoniXBot"):  # type: ignore
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = self.name_input.value.strip()
        if hasattr(self.bot, "db") and self.bot.db:
            pl_id = await self.bot.db.create_playlist(user_id=interaction.user.id, name=name, is_public=False)
            if pl_id:
                await interaction.response.send_message(
                    embed=create_success_embed("Playlist Created", f"Successfully created playlist **{name}**!"),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Duplicate Playlist", f"You already have a playlist named **{name}**."),
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                embed=create_error_embed("Database Error", "Database service is not ready."),
                ephemeral=True,
            )
