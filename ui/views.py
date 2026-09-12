"""Interactive UI views, control panels, menus, and pagination."""

from typing import List, Optional
import discord
from discord import ui
from music.queue import LoopMode
from music.filters import FilterPreset
from utils.permissions import has_dj_permissions
from utils.validators import format_duration
from ui.embeds import (
    create_now_playing_embed,
    create_queue_embed,
    create_lyrics_embed,
    create_success_embed,
    create_error_embed,
)
from ui.modals import VolumeModal


async def disable_view_components(message: discord.Message) -> None:
    """Disable all buttons and selects on an existing message view."""
    view = ui.View.from_message(message)
    if view:
        for child in view.children:
            child.disabled = True
        try:
            await message.edit(view=view)
        except Exception:
            pass


class FilterSelect(ui.Select):
    """Dropdown for applying live audio effects."""

    def __init__(self, current_preset: FilterPreset):
        options = [
            discord.SelectOption(label="Normal / Flat", value=FilterPreset.FLAT.value, emoji="🎚️"),
            discord.SelectOption(label="Bass Boost (Low)", value=FilterPreset.BASSBOOST_LOW.value, emoji="🔊"),
            discord.SelectOption(label="Bass Boost (Medium)", value=FilterPreset.BASSBOOST_MED.value, emoji="💥"),
            discord.SelectOption(label="Bass Boost (High)", value=FilterPreset.BASSBOOST_HIGH.value, emoji="💣"),
            discord.SelectOption(label="Nightcore", value=FilterPreset.NIGHTCORE.value, emoji="⚡"),
            discord.SelectOption(label="Vaporwave", value=FilterPreset.VAPORWAVE.value, emoji="🌊"),
            discord.SelectOption(label="8D Audio", value=FilterPreset.ROTATION_8D.value, emoji="🎧"),
            discord.SelectOption(label="Pop EQ", value=FilterPreset.POP.value, emoji="🎤"),
            discord.SelectOption(label="Rock EQ", value=FilterPreset.ROCK.value, emoji="🎸"),
            discord.SelectOption(label="Electronic EQ", value=FilterPreset.ELECTRONIC.value, emoji="🎹"),
        ]
        super().__init__(
            placeholder="Select Audio Equalizer / Filter...",
            min_values=1,
            max_values=1,
            options=options,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: "PlayerControlView" = self.view  # type: ignore
        player = view.player

        # Verify voice connection
        if not interaction.user.voice or interaction.user.voice.channel != player.channel:
            await interaction.response.send_message("You must be in the same voice channel.", ephemeral=True)
            return

        selected = FilterPreset(self.values[0])
        await player.apply_filter_preset(selected)
        await interaction.response.send_message(
            embed=create_success_embed("Filter Applied", f"Active filter set to **{selected.value.title()}**."),
            ephemeral=True,
        )
        await player.refresh_controller()


class PlayerControlView(ui.View):
    """Main interactive Now Playing control dashboard."""

    def __init__(self, player: "HarmoniXPlayer"):  # type: ignore
        super().__init__(timeout=None)
        self.player = player
        self.add_item(FilterSelect(player.active_preset))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False

        if not interaction.user.voice or interaction.user.voice.channel != self.player.channel:
            await interaction.response.send_message(
                "You must be in the same voice channel as HarmoniX to use these controls.",
                ephemeral=True,
            )
            return False
        return True

    @ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        # Seek to start or pop previous track
        if self.player.position > 5000:
            await self.player.seek(0)
            await interaction.response.send_message("Restarted current track.", ephemeral=True)
        else:
            prev = await self.player.queue.get_previous()
            if prev:
                await self.player.play_next()
                await interaction.response.send_message(f"Replaying: **{prev.title}**", ephemeral=True)
            else:
                await interaction.response.send_message("No previous track in history.", ephemeral=True)
        await self.player.refresh_controller()

    @ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, row=0)
    async def play_pause_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if self.player.paused:
            await self.player.pause(False)
            await interaction.response.send_message("Resumed playback.", ephemeral=True)
        else:
            await self.player.pause(True)
            await interaction.response.send_message("Paused playback.", ephemeral=True)
        await self.player.refresh_controller()

    @ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def skip_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.send_message("Skipped track.", ephemeral=True)
        await self.player.play_next()

    @ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.send_message("Stopped playback and cleared queue.", ephemeral=True)
        await self.player.teardown()

    @ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self.player.queue.shuffle()
        await interaction.response.send_message("🔀 Shuffled the upcoming queue.", ephemeral=True)
        await self.player.refresh_controller()

    @ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def loop_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        new_mode = self.player.queue.toggle_loop()
        mode_names = {LoopMode.OFF: "Disabled", LoopMode.TRACK: "Single Track", LoopMode.QUEUE: "Entire Queue"}
        await interaction.response.send_message(f"Loop mode set to **{mode_names[new_mode]}**.", ephemeral=True)
        await self.player.refresh_controller()

    @ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def volume_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.send_modal(VolumeModal(self.player))

    @ui.button(emoji="📑", style=discord.ButtonStyle.secondary, row=1)
    async def queue_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        embed = create_queue_embed(self.player.queue, self.player.current_harmoni_track, page=1)
        view = QueuePaginationView(self.player.queue, self.player.current_harmoni_track)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class QueuePaginationView(ui.View):
    """Interactive pagination for queue inspection."""

    def __init__(
        self,
        queue: "HarmoniXQueue",  # type: ignore
        current_track: Optional["HarmoniXTrack"],  # type: ignore
        per_page: int = 10,
    ):
        super().__init__(timeout=120)
        self.queue = queue
        self.current_track = current_track
        self.per_page = per_page
        self.current_page = 1
        self.total_pages = max((len(queue.tracks) + per_page - 1) // per_page, 1)

    @ui.button(label="◀ Prev", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            embed = create_queue_embed(self.queue, self.current_track, page=self.current_page, per_page=self.per_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            embed = create_queue_embed(self.queue, self.current_track, page=self.current_page, per_page=self.per_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()


class SearchSelectView(ui.View):
    """Dropdown selection menu for interactive track searching."""

    def __init__(
        self,
        tracks: List["HarmoniXTrack"],  # type: ignore
        requester: discord.Member,
        player: "HarmoniXPlayer",  # type: ignore
    ):
        super().__init__(timeout=60)
        self.tracks = tracks[:10]
        self.requester = requester
        self.player = player

        options = []
        for i, track in enumerate(self.tracks):
            title = track.title[:80]
            desc = f"{track.author[:40]} • {track.duration_str}"
            options.append(
                discord.SelectOption(
                    label=f"{i+1}. {title}",
                    description=desc,
                    value=str(i),
                    emoji="🎵",
                )
            )

        self.select_menu = ui.Select(
            placeholder="Select a song to play...",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.select_menu.callback = self.on_select_track
        self.add_item(self.select_menu)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("Only the person who initiated the search can choose.", ephemeral=True)
            return False
        return True

    async def on_select_track(self, interaction: discord.Interaction) -> None:
        index = int(self.select_menu.values[0])
        selected_track = self.tracks[index]
        selected_track.requester = interaction.user  # type: ignore

        is_playing = self.player.playing
        await self.player.queue.put(selected_track)

        if not is_playing:
            await self.player.play_next()
            await interaction.response.edit_message(
                embed=create_success_embed("Now Playing", f"Playing [{selected_track.title}]({selected_track.uri})!"),
                view=None,
            )
        else:
            pos = len(self.player.queue)
            from ui.embeds import create_track_queued_embed
            await interaction.response.edit_message(
                embed=create_track_queued_embed(selected_track, position=pos),
                view=None,
            )

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.edit_message(
            embed=create_error_embed("Search Cancelled", "Track selection was dismissed."),
            view=None,
        )


class LyricsPaginationView(ui.View):
    """Pagination view for long lyrics."""

    def __init__(self, title: str, artist: str, pages: List[str]):
        super().__init__(timeout=120)
        self.title = title
        self.artist = artist
        self.pages = pages
        self.current_page = 1
        self.total_pages = len(pages)

    @ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            embed = create_lyrics_embed(
                self.title, self.artist, self.pages[self.current_page - 1], self.current_page, self.total_pages
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            embed = create_lyrics_embed(
                self.title, self.artist, self.pages[self.current_page - 1], self.current_page, self.total_pages
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
