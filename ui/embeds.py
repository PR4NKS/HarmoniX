"""Discord UI embed builders with rich branding, icons, and progress bars."""

from typing import Optional, List
import discord
from config.settings import get_settings
from music.track import HarmoniXTrack
from music.queue import HarmoniXQueue, LoopMode
from utils.validators import format_duration, create_progress_bar

settings = get_settings()


def create_now_playing_embed(player: "HarmoniXPlayer") -> discord.Embed:  # type: ignore
    """Build the high-fidelity Now Playing control embed."""
    track: Optional[HarmoniXTrack] = player.current_harmoni_track
    if not track:
        embed = discord.Embed(
            title="🎵 Nothing Currently Playing",
            description="Use `/play <query or url>` to start listening!",
            color=settings.COLOR_SECONDARY,
        )
        return embed

    embed = discord.Embed(
        title=f"Now Playing: {track.title}",
        url=track.uri if track.uri else None,
        color=settings.COLOR_PRIMARY,
    )

    if track.artwork:
        embed.set_thumbnail(url=track.artwork)

    # Calculate playback progress
    current_ms = player.position if hasattr(player, "position") else 0
    total_ms = track.length
    progress_bar = create_progress_bar(current_ms, total_ms, length=14)
    current_time_str = format_duration(current_ms)
    total_time_str = track.duration_str

    embed.description = f"**{track.author}**\n\n`{current_time_str}` {progress_bar} `{total_time_str}`\n"

    # Status indicators
    status_icon = "⏸️ Paused" if player.paused else "▶️ Playing"
    loop_icon = "🔁 Off"
    if player.queue.loop_mode == LoopMode.TRACK:
        loop_icon = "🔂 Track"
    elif player.queue.loop_mode == LoopMode.QUEUE:
        loop_icon = "🔁 Queue"

    filter_name = player.active_preset.value.replace("_", " ").title()

    embed.add_field(name="Status", value=f"`{status_icon}`", inline=True)
    embed.add_field(name="Volume", value=f"`🔊 {player.volume}%`", inline=True)
    embed.add_field(name="Loop", value=f"`{loop_icon}`", inline=True)

    embed.add_field(name="Filter", value=f"`🎛️ {filter_name}`", inline=True)
    embed.add_field(name="Queue", value=f"`📑 {len(player.queue)} tracks`", inline=True)
    embed.add_field(name="Requested By", value=track.requester_mention, inline=True)

    embed.set_footer(
        text=f"{settings.BOT_NAME} • High-Fidelity Audio Platform",
        icon_url=player.guild.icon.url if player.guild and player.guild.icon else None,
    )
    return embed


def create_track_queued_embed(track: HarmoniXTrack, position: int) -> discord.Embed:
    """Build embed notification for a queued track."""
    embed = discord.Embed(
        title="Added to Queue",
        description=f"[{track.title}]({track.uri})\nby **{track.author}**",
        color=settings.COLOR_SUCCESS,
    )
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)

    embed.add_field(name="Duration", value=f"`{track.duration_str}`", inline=True)
    embed.add_field(name="Position in Queue", value=f"`#{position}`", inline=True)
    embed.add_field(name="Requested By", value=track.requester_mention, inline=True)
    return embed


def create_playlist_queued_embed(
    playlist_name: str,
    track_count: int,
    requester: discord.Member,
    thumbnail_url: Optional[str] = None,
) -> discord.Embed:
    """Build embed notification for an imported playlist."""
    embed = discord.Embed(
        title="Playlist Enqueued",
        description=f"Successfully imported **{playlist_name}** with **{track_count}** tracks.",
        color=settings.COLOR_SUCCESS,
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    embed.add_field(name="Tracks Added", value=f"`{track_count}`", inline=True)
    embed.add_field(name="Requested By", value=requester.mention, inline=True)
    return embed


def create_queue_embed(
    queue: HarmoniXQueue,
    current_track: Optional[HarmoniXTrack] = None,
    page: int = 1,
    per_page: int = 10,
) -> discord.Embed:
    """Build paginated queue inspection embed."""
    tracks = queue.tracks
    total_tracks = len(tracks)
    total_pages = max((total_tracks + per_page - 1) // per_page, 1)
    page = max(1, min(page, total_pages))

    embed = discord.Embed(
        title=f"📑 Server Music Queue (Page {page}/{total_pages})",
        color=settings.COLOR_PRIMARY,
    )

    if current_track:
        embed.add_field(
            name="Now Playing",
            value=f"▶️ [{current_track.title}]({current_track.uri}) | `{current_track.duration_str}` | {current_track.requester_mention}",
            inline=False,
        )

    if not tracks:
        embed.description = "The queue is currently empty. Use `/play` to add more songs!"
    else:
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        entries = []
        for i, t in enumerate(tracks[start_idx:end_idx], start=start_idx + 1):
            entries.append(f"`{i:2d}.` [{t.title[:45]}]({t.uri}) • `{t.duration_str}` • {t.requester_mention}")

        embed.description = "\n".join(entries)

    total_duration_str = format_duration(queue.total_duration)
    embed.set_footer(text=f"Total: {total_tracks} tracks | Duration: {total_duration_str} | Loop: {queue.loop_mode.value.title()}")
    return embed


def create_success_embed(title: str, description: str) -> discord.Embed:
    """Standard success feedback embed."""
    return discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=settings.COLOR_SUCCESS,
    )


def create_error_embed(title: str, description: str) -> discord.Embed:
    """Standard error notification embed."""
    return discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=settings.COLOR_ERROR,
    )


def create_info_embed(title: str, description: str) -> discord.Embed:
    """Standard neutral informational embed."""
    return discord.Embed(
        title=title,
        description=description,
        color=settings.COLOR_PRIMARY,
    )


def create_lyrics_embed(
    title: str,
    artist: str,
    lyrics_page: str,
    current_page: int,
    total_pages: int,
) -> discord.Embed:
    """Lyrics embed with page counter."""
    embed = discord.Embed(
        title=f"🎤 Lyrics: {title}",
        description=f"**Artist:** {artist}\n\n{lyrics_page}",
        color=settings.COLOR_PRIMARY,
    )
    embed.set_footer(text=f"Page {current_page}/{total_pages} • Powered by HarmoniX Lyrics")
    return embed
