"""Thread-safe and async-safe guild music queue system with history and loop modes."""

import asyncio
import random
from collections import deque
from enum import Enum
from typing import Optional, List, Deque
from .track import HarmoniXTrack
from bot.errors import QueueEmptyError, QueueFullError, InvalidTrackIndexError


class LoopMode(Enum):
    """Looping states for the queue."""
    OFF = "off"
    TRACK = "track"
    QUEUE = "queue"


class HistoryQueue:
    """History container compatible with both deque operations and wavelink.Queue expectations."""

    def __init__(self, maxlen: int = 50):
        self._deque: Deque[HarmoniXTrack] = deque(maxlen=maxlen)

    def put(self, item: HarmoniXTrack) -> None:
        self._deque.append(item)

    def append(self, item: HarmoniXTrack) -> None:
        self._deque.append(item)

    def pop(self) -> HarmoniXTrack:
        return self._deque.pop()

    def clear(self) -> None:
        self._deque.clear()

    def __iter__(self):
        return iter(self._deque)

    def __len__(self) -> int:
        return len(self._deque)

    def __getitem__(self, index):
        return self._deque[index]

    def __bool__(self) -> bool:
        return len(self._deque) > 0


class HarmoniXQueue:
    """Per-guild queue data structure with loop modes, history, and concurrency guards."""

    def __init__(self, max_size: int = 500, history_limit: int = 50):
        self.max_size = max_size
        self.history_limit = history_limit
        self.loop_mode = LoopMode.OFF
        self.prevent_duplicates = False

        self._queue: Deque[HarmoniXTrack] = deque()
        self._history = HistoryQueue(maxlen=history_limit)
        self._current_track: Optional[HarmoniXTrack] = None
        self._lock = asyncio.Lock()

    @property
    def current(self) -> Optional[HarmoniXTrack]:
        """Currently playing track."""
        return self._current_track

    @current.setter
    def current(self, track: Optional[HarmoniXTrack]) -> None:
        self._current_track = track

    def __len__(self) -> int:
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def tracks(self) -> List[HarmoniXTrack]:
        """List snapshot of tracks currently in queue."""
        return list(self._queue)

    @property
    def history(self) -> List[HarmoniXTrack]:
        """List snapshot of recently played tracks."""
        return list(self._history)

    @property
    def total_duration(self) -> int:
        """Total duration of upcoming tracks in milliseconds."""
        return sum(t.length for t in self._queue)

    async def put(self, track: HarmoniXTrack) -> None:
        """Add a single track to the end of the queue."""
        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise QueueFullError(self.max_size)

            if self.prevent_duplicates and any(t.uri == track.uri for t in self._queue):
                return

            self._queue.append(track)

    async def put_tracks(self, tracks: List[HarmoniXTrack]) -> int:
        """Add multiple tracks to the queue up to maximum limit. Returns count added."""
        async with self._lock:
            added = 0
            for track in tracks:
                if len(self._queue) >= self.max_size:
                    break
                if self.prevent_duplicates and any(t.uri == track.uri for t in self._queue):
                    continue
                self._queue.append(track)
                added += 1
            return added

    async def put_front(self, track: HarmoniXTrack) -> None:
        """Add a track directly to the front (play next)."""
        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise QueueFullError(self.max_size)
            self._queue.appendleft(track)

    async def get(self) -> Optional[HarmoniXTrack]:
        """Retrieve the next track considering the active loop mode."""
        async with self._lock:
            # If looping current track and current track exists, return current
            if self.loop_mode == LoopMode.TRACK and self._current_track is not None:
                return self._current_track

            # If looping queue and current track finished, append previous back to end
            if self.loop_mode == LoopMode.QUEUE and self._current_track is not None:
                self._queue.append(self._current_track)

            # Record current to history if switching
            if self._current_track is not None and self.loop_mode != LoopMode.TRACK:
                self._history.append(self._current_track)

            if not self._queue:
                self._current_track = None
                return None

            next_track = self._queue.popleft()
            self._current_track = next_track
            return next_track

    async def remove(self, index: int) -> HarmoniXTrack:
        """Remove a track at 1-based index."""
        async with self._lock:
            if index < 1 or index > len(self._queue):
                raise InvalidTrackIndexError(index)
            # Deque does not support fast index deletion directly, convert to list
            tracks_list = list(self._queue)
            removed = tracks_list.pop(index - 1)
            self._queue = deque(tracks_list)
            return removed

    async def move(self, from_index: int, to_index: int) -> HarmoniXTrack:
        """Move a track from one 1-based position to another."""
        async with self._lock:
            total = len(self._queue)
            if from_index < 1 or from_index > total:
                raise InvalidTrackIndexError(from_index)
            if to_index < 1 or to_index > total:
                raise InvalidTrackIndexError(to_index)

            tracks_list = list(self._queue)
            track = tracks_list.pop(from_index - 1)
            tracks_list.insert(to_index - 1, track)
            self._queue = deque(tracks_list)
            return track

    async def jump_to(self, index: int) -> HarmoniXTrack:
        """Skip directly to a 1-based track index, discarding intermediate tracks."""
        async with self._lock:
            if index < 1 or index > len(self._queue):
                raise InvalidTrackIndexError(index)

            # Discard preceding tracks and push to history
            for _ in range(index - 1):
                discarded = self._queue.popleft()
                self._history.append(discarded)

            if self._current_track:
                self._history.append(self._current_track)

            target = self._queue.popleft()
            self._current_track = target
            return target

    async def shuffle(self) -> None:
        """Randomly shuffle the pending queue."""
        async with self._lock:
            if len(self._queue) < 2:
                return
            tracks_list = list(self._queue)
            random.shuffle(tracks_list)
            self._queue = deque(tracks_list)

    async def reverse(self) -> None:
        """Reverse the order of tracks in the queue."""
        async with self._lock:
            self._queue.reverse()

    async def clear(self) -> int:
        """Clear all pending tracks. Returns number of tracks cleared."""
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    async def get_previous(self) -> Optional[HarmoniXTrack]:
        """Retrieve the most recently played track from history."""
        async with self._lock:
            if not self._history:
                return None
            prev = self._history.pop()
            if self._current_track:
                self._queue.appendleft(self._current_track)
            self._current_track = prev
            return prev

    def set_loop_mode(self, mode: LoopMode) -> LoopMode:
        """Update active loop mode."""
        self.loop_mode = mode
        return self.loop_mode

    def toggle_loop(self) -> LoopMode:
        """Cycle through loop modes: OFF -> TRACK -> QUEUE -> OFF."""
        if self.loop_mode == LoopMode.OFF:
            self.loop_mode = LoopMode.TRACK
        elif self.loop_mode == LoopMode.TRACK:
            self.loop_mode = LoopMode.QUEUE
        else:
            self.loop_mode = LoopMode.OFF
        return self.loop_mode
