"""Internet radio streams, Shoutcast, Icecast, and curated presets."""

from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands
from discord.ext import commands

from music.player import HarmoniXPlayer
from utils.permissions import check_voice_state
from ui.embeds import create_success_embed, create_info_embed, create_error_embed
from bot.errors import BotNotInVoiceChannel

if TYPE_CHECKING:
    from bot.client import HarmoniXBot

RADIO_PRESETS = {
    "lofi": {
        "name": "Lofi Hip Hop Radio ☕",
        "url": "https://stream.zeno.fm/f3wvbbqmdg8uv",
        "description": "24/7 chilled beats to study and relax to.",
    },
    "synthwave": {
        "name": "Nightwave Plaza / Synthwave 🌌",
        "url": "https://radio.plaza.one/mp3",
        "description": "Pure retro vaporwave & synthwave 80s aesthetic.",
    },
    "jazz": {
        "name": "Smooth Jazz 🎷",
        "url": "https://streaming.exclusive.radio/er/smoothjazz/icecast.audio",
        "description": "24/7 relaxing modern & classic smooth jazz.",
    },
    "classic_rock": {
        "name": "Classic Rock FM 🎸",
        "url": "https://media-ssl.musicradio.com/ClassicRock",
        "description": "Greatest rock anthems of all time.",
    },
    "chillout": {
        "name": "Chillout Lounge 🌴",
        "url": "https://stream.zeno.fm/0r0xa792kwzuv",
        "description": "Ambient deep house and chillout tunes.",
    },
}


class RadioCog(commands.Cog, name="Radio"):
    """Online web radio and live stream broadcasting."""

    def __init__(self, bot: "HarmoniXBot"):
        self.bot = bot

    radio_group = app_commands.Group(name="radio", description="Internet radio and stream broadcasting")

    @radio_group.command(name="play", description="Stream a web radio preset or a custom direct stream URL.")
    @app_commands.describe(
        preset="Choose a curated live radio station preset",
        custom_url="Direct Icecast/Shoutcast/MP3 audio stream URL",
    )
    @app_commands.choices(
        preset=[
            app_commands.Choice(name="☕ Lofi Hip Hop Beats", value="lofi"),
            app_commands.Choice(name="🌌 Synthwave & Vaporwave", value="synthwave"),
            app_commands.Choice(name="🎷 Smooth Jazz Radio", value="jazz"),
            app_commands.Choice(name="🎸 Classic Rock FM", value="classic_rock"),
            app_commands.Choice(name="🌴 Chillout Lounge", value="chillout"),
        ]
    )
    async def play(
        self,
        interaction: discord.Interaction,
        preset: Optional[app_commands.Choice[str]] = None,
        custom_url: Optional[str] = None,
    ) -> None:
        await interaction.response.defer()

        target_url = None
        station_name = "Custom Radio Stream"

        if preset:
            p_data = RADIO_PRESETS[preset.value]
            target_url = p_data["url"]
            station_name = p_data["name"]
        elif custom_url:
            target_url = custom_url.strip()
        else:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Missing Station", "Please select a preset station or provide a custom stream URL."
                )
            )
            return

        player = await self.bot.music.get_or_create_player(interaction, connect=True)
        results = await self.bot.music.resolve_query(target_url, requester=interaction.user)  # type: ignore

        if not results:
            await interaction.followup.send(
                embed=create_error_embed("Stream Error", f"Could not connect to stream at `{target_url}`.")
            )
            return

        track = results[0] if isinstance(results, list) else results.tracks[0]
        # Clear existing queue for uninterrupted live radio stream
        await player.queue.clear()
        await player.queue.put(track)
        await player.play_next()

        embed = create_success_embed(
            "Radio Streaming",
            f"Now broadcasting **{station_name}** live in {player.channel.mention}!",
        )
        await interaction.followup.send(embed=embed)

    @radio_group.command(name="list", description="List available curated radio presets.")
    async def list_presets(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="📻 HarmoniX Curated Radio Presets",
            description="Use `/radio play <preset>` to tune in directly.",
            color=self.bot.settings.COLOR_PRIMARY,
        )
        for key, val in RADIO_PRESETS.items():
            embed.add_field(name=val["name"], value=val["description"], inline=False)

        await interaction.response.send_message(embed=embed)

    @radio_group.command(name="stop", description="Stop radio broadcast.")
    async def stop(self, interaction: discord.Interaction) -> None:
        check_voice_state(interaction, require_bot=True, require_same_channel=True)
        player: Optional[HarmoniXPlayer] = interaction.guild.voice_client  # type: ignore
        if not player:
            raise BotNotInVoiceChannel()

        await player.teardown()
        await interaction.response.send_message(embed=create_info_embed("Radio Stopped", "Broadcast terminated."))


async def setup(bot: "HarmoniXBot") -> None:
    await bot.add_cog(RadioCog(bot))
