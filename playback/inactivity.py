import asyncio

from discord import Guild
from discord.abc import Messageable

# Stores active inactivity timers per guild
inactivity_timers: dict[int, asyncio.Task] = {}


async def leave_after_delay(
    guild: Guild, channel: Messageable, delay: int = 180
) -> None:
    """
    Waits for `delay` seconds, then sends a message to the text channel
    and disconnects the bot from the voice channel if no activity has occurred.

    :param guild: Discord guild (server) object.
    :param channel: Text channel to send inactivity message in.
    :param delay: Time in seconds before leaving due to inactivity (default: 180).
    """
    await asyncio.sleep(delay)

    voice_client = guild.voice_client
    # Still connected but not playing (a new song cancels the timer, but guard
    # against racing it anyway)
    if voice_client and not voice_client.is_playing():  # type: ignore
        await channel.send(
            "No activity detected. Leaving the voice channel due to inactivity."
        )
        await voice_client.disconnect(force=True)


def start_timer(guild: Guild, channel: Messageable, delay: int = 180) -> None:
    """
    Starts or restarts an inactivity timer for the given guild.
    Cancels any existing timer for that guild to avoid overlaps.

    :param guild: Discord guild (server) object.
    :param channel: Text channel to send inactivity message in.
    :param delay: Time in seconds before leaving due to inactivity (default: 180).
    """
    cancel_timer(guild.id)
    inactivity_timers[guild.id] = asyncio.create_task(
        leave_after_delay(guild, channel, delay)
    )


def cancel_timer(guild_id: int) -> None:
    """Cancels the guild's inactivity timer, if one is running."""
    timer = inactivity_timers.pop(guild_id, None)
    if timer is not None:
        timer.cancel()
