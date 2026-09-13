"""Internal audio streaming proxy server for seamless YouTube audio playback."""

import asyncio
import re
import socket
from typing import Optional, Dict, Any, Tuple, Union
import aiohttp
from aiohttp import web
import yt_dlp
import wavelink
import discord
from music.track import HarmoniXTrack
from utils.logging import get_logger

logger = get_logger(__name__)

_stream_server_instance: Optional["StreamServer"] = None


def get_stream_server() -> Optional["StreamServer"]:
    """Retrieve global StreamServer singleton instance."""
    return _stream_server_instance


class StreamServer:
    """Lightweight local HTTP streaming proxy that delivers YouTube audio streams to Lavalink."""

    def __init__(self, host: str = "0.0.0.0", port: int = 2334, callback_host: str = "127.0.0.1"):
        self.host = host
        self.port = port
        self.callback_host = callback_host
        self.actual_port = port
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}  # key -> (info, timestamp)
        self.is_running: bool = False
        global _stream_server_instance
        _stream_server_instance = self

    def _find_available_port(self, start_port: int, max_attempts: int = 20) -> int:
        """Find an open TCP port starting from start_port."""
        for p in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind((self.host, p))
                    return p
                except OSError:
                    continue
        return start_port

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, sock_read=60))
        return self._session

    async def start(self) -> None:
        """Start the local streaming web server."""
        if self.is_running:
            return

        self.actual_port = self._find_available_port(self.port)
        self._app = web.Application()
        self._app.router.add_route("*", "/stream/{video_id}", self._handle_stream)
        self._app.router.add_route("*", "/stream", self._handle_stream)
        self._app.router.add_get("/health", self._handle_health)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.host, self.actual_port)
        await self._site.start()
        self.is_running = True
        logger.info("HarmoniX Stream Proxy running on http://%s:%d", self.host, self.actual_port)

    async def stop(self) -> None:
        """Gracefully stop the streaming server."""
        self.is_running = False
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("HarmoniX Stream Proxy stopped.")

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.Response(text="OK", status=200)

    def extract_info(self, target: str) -> Optional[Dict[str, Any]]:
        """Synchronously extract media info and stream URL using yt-dlp."""
        ydl_opts = {
            "format": "bestaudio/best[height<=720]/best",
            "format_sort": ["abr:desc", "asr:desc", "quality:desc"],
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "nocheckcertificate": True,
            "extract_flat": False,
            "noplaylist": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }

        query = target.strip()
        if not query.startswith("http://") and not query.startswith("https://"):
            if len(query) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", query):
                query = f"https://www.youtube.com/watch?v={query}"
            else:
                query = f"ytsearch1:{query}"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = ydl.extract_info(query, download=False)
                if not data:
                    return None
                if "entries" in data and data["entries"]:
                    data = data["entries"][0]
                return data
        except Exception as e:
            logger.warning("yt-dlp extraction failed for %s: %s", target, e)
            return None

    async def get_track_info(self, target: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Extract media info with caching."""
        loop = asyncio.get_running_loop()
        now = loop.time()

        clean_key = re.sub(r"\.[a-zA-Z0-9]+$", "", target) if not target.startswith("http") else target
        if not force_refresh:
            for key in (clean_key, target):
                if key in self._cache:
                    info, timestamp = self._cache[key]
                    if now - timestamp < 14400:  # 4 hours validity
                        return info

        info = await loop.run_in_executor(None, self.extract_info, target)
        if info:
            self._cache[target] = (info, now)
            self._cache[clean_key] = (info, now)
            vid = info.get("id")
            if vid:
                self._cache[vid] = (info, now)
                self._cache[f"https://www.youtube.com/watch?v={vid}"] = (info, now)
        return info

    async def _handle_stream(self, request: web.Request) -> web.StreamResponse:
        """Handle incoming audio stream requests from Lavalink."""
        video_id = request.match_info.get("video_id")
        if not video_id:
            video_id = request.query.get("v") or request.query.get("url") or request.query.get("q")

        if not video_id:
            return web.Response(text="Missing video parameter", status=400)

        # Strip file extensions if present (including .mp4, .webm, .m4a, etc.)
        raw_target = re.sub(r"\.[a-zA-Z0-9]+$", "", video_id)

        info = await self.get_track_info(raw_target)
        if not info or not info.get("url"):
            return web.Response(text="Could not resolve media stream", status=404)

        ext = info.get("ext", "mp4")
        expected_content_type = "audio/mp4" if ext in ("mp4", "m4a") else f"audio/{ext}"

        # Check HEAD request early
        if request.method == "HEAD":
            return web.Response(
                status=200,
                headers={
                    "Content-Type": expected_content_type,
                    "Accept-Ranges": "bytes",
                },
            )

        session = await self._get_session()
        upstream_url = info["url"]
        upstream_headers = dict(info.get("http_headers", {}))

        # Forward Range header if Lavalink specified it
        if "Range" in request.headers:
            upstream_headers["Range"] = request.headers["Range"]

        try:
            upstream_resp = await session.get(upstream_url, headers=upstream_headers)
        except Exception as e:
            logger.error("Failed to connect to media CDN: %s", e)
            return web.Response(text="Upstream connection error", status=502)

        # If CDN returned 403 (e.g. token expired), refresh once
        if upstream_resp.status in (403, 410):
            logger.info("Upstream stream URL expired for %s (status %d). Refreshing...", raw_target, upstream_resp.status)
            upstream_resp.close()
            info = await self.get_track_info(raw_target, force_refresh=True)
            if not info or not info.get("url"):
                return web.Response(text="Stream refresh failed", status=502)

            upstream_url = info["url"]
            upstream_headers = dict(info.get("http_headers", {}))
            if "Range" in request.headers:
                upstream_headers["Range"] = request.headers["Range"]
            try:
                upstream_resp = await session.get(upstream_url, headers=upstream_headers)
            except Exception as e:
                logger.error("Retry connection failed: %s", e)
                return web.Response(text="Upstream connection error", status=502)

        content_type = upstream_resp.headers.get("Content-Type", expected_content_type)
        if content_type == "video/mp4":
            content_type = "audio/mp4"

        resp_headers = {
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
        }
        if "Content-Range" in upstream_resp.headers:
            resp_headers["Content-Range"] = upstream_resp.headers["Content-Range"]

        resp = web.StreamResponse(
            status=upstream_resp.status,
            headers=resp_headers,
        )
        if "Content-Length" in upstream_resp.headers:
            try:
                resp.content_length = int(upstream_resp.headers["Content-Length"])
            except ValueError:
                pass

        try:
            await resp.prepare(request)
            async for chunk in upstream_resp.content.iter_chunked(64 * 1024):
                await resp.write(chunk)
        except (asyncio.CancelledError, ConnectionResetError, aiohttp.ClientConnectionResetError):
            pass
        except Exception as stream_err:
            logger.debug("Streaming interrupted: %s", stream_err)
        finally:
            upstream_resp.close()
            try:
                await resp.write_eof()
            except Exception:
                pass

        return resp

    async def resolve_playable(
        self,
        target: str,
        requester: Optional[discord.Member] = None,
    ) -> Optional[HarmoniXTrack]:
        """Resolve a YouTube target into a HarmoniXTrack streamed via this local proxy."""
        if not self.is_running:
            return None

        info = await self.get_track_info(target)
        if not info:
            return None

        video_id = info.get("id")
        if not video_id:
            return None

        ext = info.get("ext", "mp4")
        stream_url = f"http://{self.callback_host}:{self.actual_port}/stream/{video_id}.{ext}"
        try:
            results = await wavelink.Playable.search(stream_url)
            if not results:
                return None

            playable = results[0]
            title = info.get("title") or getattr(playable, "title", "YouTube Track")
            author = info.get("uploader") or getattr(playable, "author", "YouTube Artist")
            duration_sec = info.get("duration")
            length = int(duration_sec * 1000) if duration_sec else getattr(playable, "length", 0)
            thumbnail = info.get("thumbnail") or getattr(playable, "artwork", None)
            real_uri = f"https://www.youtube.com/watch?v={video_id}"

            return HarmoniXTrack(
                playable=playable,
                requester=requester,
                source_name="youtube",
                title=title,
                author=author,
                length=length,
                uri=real_uri,
                artwork=thumbnail,
            )
        except Exception as e:
            logger.warning("Failed creating playable from stream proxy: %s", e)
            return None
