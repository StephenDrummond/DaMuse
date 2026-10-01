import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

import discord

from utils.audio_resolver import Track
from utils.profiler import PlayRecord


@dataclass
class GuildPlayer:
    """Playback state for one guild. A guild has at most one voice connection
    and it lives in whichever process owns the guild's shard, so this state is
    deliberately in-process: nothing else could act on it anyway."""

    queue: Deque[Track] = field(default_factory=deque)
    current: Optional[Track] = None
    # resolves to the `plays` row for `current` (None if it couldn't be
    # identified); a task so playback never waits on Spotify / Postgres
    current_play: Optional["asyncio.Task[Optional[PlayRecord]]"] = None
    skipped: bool = False  # current song ended via !skip, not naturally
    stopping: bool = False  # !stop: don't advance when the current song ends
    text_channel: Optional[discord.abc.Messageable] = None  # for announcements
    # serializes "start the next song" so concurrent !play / track-end
    # callbacks can't both start playback
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
