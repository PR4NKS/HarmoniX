"""Interactive categorized help system with dropdown navigation."""

from typing import Optional, List, TYPE_CHECKING
import discord
from discord import app_commands, ui
from discord.ext import commands

if TYPE_CHECKING:
    from bot.client import HarmoniXBot

HELP_CATEGORIES = {
    "music": {
        "title": "🎵 Music Playback",
        "description": "Commands to play, control, and manipulate music playback.",
        "commands": [
            ("`/play <query>`", "Play a track, playlist, or stream from YouTube, Spotify, SoundCloud, etc."),
            ("`/pause`", "Pause currently playing audio."),
            ("`/resume`", "Resume paused audio."),
            ("`/skip`", "Skip the currently playing track."),
            ("`/previous`", "Replay the previous track from history."),
            ("`/replay`", "Restart current track from 0:00."),
            ("`/stop`", "Stop playback and clear current queue."),
            ("`/volume <0-100>`", "Adjust playback volume."),
            ("`/seek <timestamp>`", "Jump to a specific timestamp in the current track."),
            ("`/nowplaying`", "Summon the interactive Now Playing control panel."),
            ("`/autoplay`", "Toggle automatic playback of related music when queue ends."),
            ("`/247`", "Toggle 24/7 continuous voice presence in the channel."),
            ("`/join`", "Connect bot to your current voice channel."),
            ("`/leave`", "Disconnect bot from voice channel."),
        ],
    },
    "queue": {
        "title": "📑 Queue Management",
        "description": "Commands for inspecting and reordering the song queue.",
        "commands": [
            ("`/queue show [page]`", "Display the upcoming server track queue."),
            ("`/queue clear`", "Clear all upcoming tracks from queue."),
            ("`/queue shuffle`", "Randomly mix up the queued songs."),
            ("`/queue remove <index>`", "Remove a specific track from the queue."),
            ("`/queue move <from> <to>`", "Move a track to a different position in the queue."),
            ("`/queue jump <index>`", "Jump directly to a specific track in queue."),
            ("`/queue reverse`", "Reverse the order of upcoming songs."),
            ("`/queue loop <mode>`", "Configure looping: Off, Track, or Queue."),
            ("`/queue history`", "View recently played songs in this server."),
            ("`/queue save <name>`", "Save current queue to database."),
            ("`/queue load <name>`", "Restore and enqueue a saved queue."),
        ],
    },
    "filters": {
        "title": "🎛️ Audio Filters & Equalizer",
        "description": "Live DSP filters and sound profiles.",
        "commands": [
            ("`/filter bassboost <level>`", "Boost lower audio frequencies (Low/Medium/High)."),
            ("`/filter nightcore`", "Speed up audio with higher pitch."),
            ("`/filter vaporwave`", "Slow down audio with relaxed pitch."),
            ("`/filter 8d`", "Apply binaural 8D rotating headphone audio."),
            ("`/filter karaoke`", "Attenuate vocals for sing-along mode."),
            ("`/filter clear`", "Reset all audio filters back to standard flat profile."),
        ],
    },
    "discovery": {
        "title": "🔍 Search & Discovery",
        "description": "Interactive search and lyrics lookup.",
        "commands": [
            ("`/search <query>`", "Search songs and pick from an interactive dropdown menu."),
            ("`/lyrics [query]`", "Display synchronized or plain lyrics with pagination."),
            ("`/trackinfo [query]`", "Inspect technical metadata and author details."),
            ("`/radio play [preset]`", "Tune in to curated 24/7 web radio stations."),
            ("`/radio list`", "List all available curated radio presets."),
        ],
    },
    "personal": {
        "title": "⭐ Favorites & Playlists",
        "description": "Personal saved collections and custom playlists.",
        "commands": [
            ("`/favorite add`", "Bookmark current song to your personal favorites."),
            ("`/favorite list`", "View your saved favorite tracks."),
            ("`/favorite play`", "Queue all your personal favorites."),
            ("`/favorite remove`", "Remove a track from favorites."),
            ("`/playlist create <name>`", "Create a named personal playlist."),
            ("`/playlist add <name> [song]`", "Add a song to your playlist."),
            ("`/playlist play <name>`", "Queue all songs from your playlist."),
            ("`/playlist list`", "List your custom playlists."),
            ("`/playlist delete <name>`", "Delete a playlist."),
        ],
    },
    "admin": {
        "title": "⚙️ Settings & System",
        "description": "Server configuration and diagnostic tools.",
        "commands": [
            ("`/settings view`", "View current server audio configuration."),
            ("`/settings dj-role <role>`", "Set required DJ role for music commands."),
            ("`/settings default-volume <lvl>`", "Configure default volume for new sessions."),
            ("`/settings max-queue <limit>`", "Set server maximum queue capacity."),
            ("`/settings auto-leave <bool>`", "Toggle automatic leave when idle/alone."),
            ("`/status`", "Inspect bot uptime, active players, and Lavalink node health."),
            ("`/ping`", "Check WebSocket and Lavalink audio latency."),
        ],
    },
}


class HelpSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Music Playback", value="music", emoji="🎵"),
            discord.SelectOption(label="Queue Management", value="queue", emoji="📑"),
            discord.SelectOption(label="Audio Filters", value="filters", emoji="🎛️"),
            discord.SelectOption(label="Search & Discovery", value="discovery", emoji="🔍"),
            discord.SelectOption(label="Favorites & Playlists", value="personal", emoji="⭐"),
            discord.SelectOption(label="Settings & Admin", value="admin", emoji="⚙️"),
        ]
        super().__init__(placeholder="Select a category to explore...", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        cat_key = self.values[0]
        cat = HELP_CATEGORIES[cat_key]

        embed = discord.Embed(
            title=f"{cat['title']}",
            description=f"{cat['description']}\n",
            color=0x5865F2,
        )
        for cmd_name, cmd_desc in cat["commands"]:
            embed.add_field(name=cmd_name, value=cmd_desc, inline=False)

        await interaction.response.edit_message(embed=embed)


class HelpView(ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())


class HelpCog(commands.Cog, name="Help"):
    """Comprehensive interactive help guide."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    @app_commands.command(name="help", description="Open the HarmoniX interactive command guide.")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title=f"🎶 Welcome to {self.bot.settings.BOT_NAME}",
            description=(
                f"**{self.bot.settings.BOT_NAME}** is a next-generation, high-fidelity Discord music bot "
                "powered by Lavalink, featuring dynamic UI control panels, multi-platform stream "
                "resolving, audio DSP filters, and queue management.\n\n"
                "**Select a category below to view commands:**"
            ),
            color=self.bot.settings.COLOR_PRIMARY,
        )
        embed.add_field(name="🎵 Music Playback", value="Play songs, playlists, streams, and adjust volume.", inline=True)
        embed.add_field(name="📑 Queue System", value="Shuffle, loop, move, save, and load queues.", inline=True)
        embed.add_field(name="🎛️ DSP Filters", value="Bass boost, 8D audio, nightcore, and vaporwave.", inline=True)
        embed.add_field(name="🔍 Discovery & Lyrics", value="Interactive track searching & synced lyrics.", inline=True)
        embed.add_field(name="⭐ Favorites & Playlists", value="Personal playlists and saved favorites.", inline=True)
        embed.add_field(name="⚙️ Server Settings", value="DJ roles, max queues, and 24/7 presence.", inline=True)

        embed.set_footer(text="HarmoniX • Production Discord Music Platform")
        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(HelpCog(bot))
