"""Queue management commands and inspection."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from music.player import HarmoniXPlayer
from music.queue import LoopMode
from utils.permissions import check_voice_state
from ui.embeds import (
    create_queue_embed,
    create_success_embed,
    create_error_embed,
    create_info_embed,
)
from ui.views import QueuePaginationView
from bot.errors import BotNotInVoiceChannel, QueueEmptyError

if TYPE_CHECKING:
    from bot.client import HarmoniXBot


class QueueCog(commands.Cog, name="Queue"):
    """Queue controls, shuffling, manipulation, history, and persistence."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    queue_group = app_commands.Group(name="queue", description="Queue control commands")

    @queue_group.command(name="show", description="Display the current server queue.")
    @app_commands.describe(page="Queue page number")
    async def show(self, interaction: discord.Interaction, page: Optional[int] = 1) -> None:
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        current_page = max(1, page or 1)
        embed = create_queue_embed(player.queue, player.current_harmoni_track, page=current_page)
        view = QueuePaginationView(player.queue, player.current_harmoni_track)
        await interaction.response.send_message(embed=embed, view=view)

    @queue_group.command(name="clear", description="Clear all songs in the queue.")
    async def clear(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        count = await player.queue.clear()
        await interaction.response.send_message(
            embed=create_success_embed("Queue Cleared", f"Removed **{count}** tracks from the queue.")
        )
        await player.refresh_controller()

    @queue_group.command(name="shuffle", description="Randomly mix the upcoming songs in the queue.")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        if len(player.queue) < 2:
            await interaction.response.send_message("Not enough tracks in queue to shuffle.", ephemeral=True)
            return

        await player.queue.shuffle()
        await interaction.response.send_message(
            embed=create_success_embed("Queue Shuffled", f"Mixed **{len(player.queue)}** tracks randomly.")
        )

    @queue_group.command(name="remove", description="Remove a specific song from the queue by its index.")
    @app_commands.describe(index="Position number of the song (e.g. 1)")
    async def remove(self, interaction: discord.Interaction, index: int) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        removed = await player.queue.remove(index)
        await interaction.response.send_message(
            embed=create_success_embed("Track Removed", f"Removed **#{index}. {removed.title}**.")
        )

    @queue_group.command(name="move", description="Move a song from one position in the queue to another.")
    @app_commands.describe(from_position="Current position number", to_position="New target position")
    async def move(self, interaction: discord.Interaction, from_position: int, to_position: int) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        track = await player.queue.move(from_position, to_position)
        await interaction.response.send_message(
            embed=create_success_embed("Track Moved", f"Moved **{track.title}** to position `#{to_position}`.")
        )

    @queue_group.command(name="jump", description="Skip straight to a specific track number in the queue.")
    @app_commands.describe(position="Position number of track to jump to")
    async def jump(self, interaction: discord.Interaction, position: int) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        target = await player.queue.jump_to(position)
        await interaction.response.send_message(
            embed=create_success_embed("Jumped to Track", f"Now playing **{target.title}**.")
        )
        await player.play_next()

    @queue_group.command(name="reverse", description="Reverse the order of tracks in the queue.")
    async def reverse(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        await player.queue.reverse()
        await interaction.response.send_message(embed=create_success_embed("Queue Reversed", "Reversed queue track order."))

    @queue_group.command(name="loop", description="Set queue looping mode.")
    @app_commands.describe(mode="Choose loop mode")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Disable Looping", value="off"),
            app_commands.Choice(name="Loop Current Track", value="track"),
            app_commands.Choice(name="Loop Entire Queue", value="queue"),
        ]
    )
    async def loop(self, interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        chosen_mode = LoopMode(mode.value)
        player.queue.set_loop_mode(chosen_mode)
        await interaction.response.send_message(
            embed=create_success_embed("Loop Mode", f"Loop mode set to **{mode.name}**.")
        )
        await player.refresh_controller()

    @queue_group.command(name="history", description="View recently played songs in this server.")
    async def history(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return

        if hasattr(self.bot, "db") and self.bot.db:
            history_entries = await self.bot.db.get_guild_history(interaction.guild.id, limit=10)
            if not history_entries:
                await interaction.response.send_message("No playback history found.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"📜 Playback History for {interaction.guild.name}",
                color=self.bot.settings.COLOR_PRIMARY,
            )
            desc = []
            for i, h in enumerate(history_entries, start=1):
                desc.append(f"`{i:2d}.` [{h.title}]({h.uri}) • `{h.author}`")
            embed.description = "\n".join(desc)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Database history service unavailable.", ephemeral=True)

    @queue_group.command(name="save", description="Save the current queue for later playback.")
    @app_commands.describe(name="Unique name for this saved queue")
    async def save(self, interaction: discord.Interaction, name: str) -> None:
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player or (player.queue.is_empty and not player.current_harmoni_track):
            await interaction.response.send_message("Nothing in the queue to save.", ephemeral=True)
            return

        all_tracks = []
        if player.current_harmoni_track:
            all_tracks.append(player.current_harmoni_track.to_dict())
        for t in player.queue.tracks:
            all_tracks.append(t.to_dict())

        if hasattr(self.bot, "db") and self.bot.db:
            success = await self.bot.db.save_queue(interaction.guild.id, name=name, tracks_data=all_tracks)
            if success:
                await interaction.response.send_message(
                    embed=create_success_embed(
                        "Queue Saved", f"Saved **{len(all_tracks)}** tracks under name `{name}`."
                    )
                )
            else:
                await interaction.response.send_message(embed=create_error_embed("Save Failed", "Failed to save queue."))

    @queue_group.command(name="load", description="Load a previously saved queue.")
    @app_commands.describe(name="Name of the saved queue to load")
    async def load(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer()
        player = await self.bot.music.get_or_create_player(interaction, connect=True)

        if hasattr(self.bot, "db") and self.bot.db:
            tracks_data = await self.bot.db.load_saved_queue(interaction.guild.id, name=name)
            if not tracks_data:
                await interaction.followup.send(embed=create_error_embed("Not Found", f"No saved queue named `{name}`."))
                return

            loaded_count = 0
            for item in tracks_data:
                query = item.get("uri") or f"{item.get('title')} {item.get('author')}"
                result = await self.bot.music.resolve_query(query, requester=interaction.user)  # type: ignore
                if result:
                    track = result[0] if isinstance(result, list) else result.tracks[0]
                    await player.queue.put(track)
                    loaded_count += 1

            if not player.playing:
                await player.play_next()

            await interaction.followup.send(
                embed=create_success_embed("Queue Loaded", f"Loaded **{loaded_count}** tracks from `{name}`!")
            )


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(QueueCog(bot))
