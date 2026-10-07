"""Composition root: builds every long-lived object once and hands them to the
bot. Cogs read `bot.services` instead of constructing their own copies."""

import logging
from dataclasses import dataclass

import discord
from discord.ext import commands

from clients.audio_store import AudioStore
from clients.spotify import SpotifyClient
from clients.youtube import YouTubeClient
from config import Settings
from db.db import Database
from audio.audio_jobs import AudioJobs
from audio.audio_resolver import AudioResolver
from taste.curator import Curator
from taste.librarian import Librarian
from taste.profiler import Profiler

logger = logging.getLogger(__name__)

EXTENSIONS = ("cogs.general", "cogs.music", "cogs.channel_events")


@dataclass
class Services:
    settings: Settings
    db: Database
    spotify: SpotifyClient
    youtube: YouTubeClient
    librarian: Librarian
    profiler: Profiler
    curator: Curator
    resolver: AudioResolver

    @classmethod
    async def create(cls, settings: Settings) -> "Services":
        """Connect to the database and build everything on top of it."""
        db = Database(settings.database)
        await db.init_pool()

        spotify = SpotifyClient(
            settings.spotify_client_id, settings.spotify_client_secret
        )
        youtube = YouTubeClient()
        librarian = Librarian(db)
        store = AudioStore.from_settings(settings.audio, settings.aws_region)
        return cls(
            settings=settings,
            db=db,
            spotify=spotify,
            youtube=youtube,
            librarian=librarian,
            profiler=Profiler(db, spotify, librarian),
            curator=Curator(db),
            resolver=AudioResolver(store, AudioJobs(db), youtube, spotify),
        )

    async def close(self) -> None:
        self.youtube.close()
        await self.db.close()


class DaMuseBot(commands.AutoShardedBot):
    """AutoShardedBot runs one shard per ~1000 guilds inside this process
    (Discord requires sharding past 2500). To spread shards across processes
    later, pass shard_ids=[...] and shard_count=N per process; all per-guild
    state is keyed by guild, so it stays with whichever process owns that
    guild's shard."""

    def __init__(self, services: Services) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.services = services

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            await self.load_extension(extension)

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (%d shards)", self.user, self.shard_count or 1)
