"""Unit tests for the HarmoniXQueue data structure and algorithms."""

import pytest
from music.queue import HarmoniXQueue, LoopMode
from music.track import HarmoniXTrack
from bot.errors import QueueFullError, InvalidTrackIndexError


@pytest.mark.asyncio
async def test_queue_add_and_get(mock_playable_factory, mock_member):
    queue = HarmoniXQueue(max_size=10)
    p1 = mock_playable_factory(title="Track 1")
    p2 = mock_playable_factory(title="Track 2")

    t1 = HarmoniXTrack(playable=p1, requester=mock_member)
    t2 = HarmoniXTrack(playable=p2, requester=mock_member)

    await queue.put(t1)
    await queue.put(t2)

    assert len(queue) == 2
    assert not queue.is_empty

    next_track = await queue.get()
    assert next_track.title == "Track 1"
    assert len(queue) == 1

    next_track2 = await queue.get()
    assert next_track2.title == "Track 2"
    assert len(queue) == 0


@pytest.mark.asyncio
async def test_queue_max_limit(mock_playable_factory, mock_member):
    queue = HarmoniXQueue(max_size=2)
    p = mock_playable_factory()

    await queue.put(HarmoniXTrack(p, mock_member))
    await queue.put(HarmoniXTrack(p, mock_member))

    with pytest.raises(QueueFullError):
        await queue.put(HarmoniXTrack(p, mock_member))


@pytest.mark.asyncio
async def test_queue_loop_modes(mock_playable_factory, mock_member):
    queue = HarmoniXQueue(max_size=10)
    p1 = mock_playable_factory(title="Song 1")
    p2 = mock_playable_factory(title="Song 2")

    await queue.put(HarmoniXTrack(p1, mock_member))
    await queue.put(HarmoniXTrack(p2, mock_member))

    # Initial get
    cur = await queue.get()
    assert cur.title == "Song 1"

    # Track loop mode
    queue.set_loop_mode(LoopMode.TRACK)
    looped = await queue.get()
    assert looped.title == "Song 1"

    # Queue loop mode
    queue.set_loop_mode(LoopMode.QUEUE)
    next_s = await queue.get()
    assert next_s.title == "Song 2"
    # Song 1 was appended to the back of queue
    assert len(queue) == 1


@pytest.mark.asyncio
async def test_queue_manipulations(mock_playable_factory, mock_member):
    queue = HarmoniXQueue(max_size=10)
    for i in range(1, 5):
        p = mock_playable_factory(title=f"Song {i}")
        await queue.put(HarmoniXTrack(p, mock_member))

    assert len(queue) == 4

    # Remove item at position 2 ("Song 2")
    removed = await queue.remove(2)
    assert removed.title == "Song 2"
    assert len(queue) == 3

    # Move item from pos 3 to pos 1
    # Current queue: Song 1, Song 3, Song 4
    moved = await queue.move(3, 1)
    assert moved.title == "Song 4"
    assert queue.tracks[0].title == "Song 4"

    # Clear
    cleared_count = await queue.clear()
    assert cleared_count == 3
    assert len(queue) == 0


@pytest.mark.asyncio
async def test_queue_history(mock_playable_factory, mock_member):
    queue = HarmoniXQueue(max_size=10)
    p1 = mock_playable_factory(title="Track A")
    p2 = mock_playable_factory(title="Track B")

    await queue.put(HarmoniXTrack(p1, mock_member))
    await queue.put(HarmoniXTrack(p2, mock_member))

    # Play Track A
    await queue.get()
    # Play Track B (Track A moves to history)
    await queue.get()

    assert len(queue.history) == 1
    assert queue.history[0].title == "Track A"

    # Get previous track
    prev = await queue.get_previous()
    assert prev.title == "Track A"
