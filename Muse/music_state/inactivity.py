import asyncio

from discord import TextChannel, Guild

# Stores active inactivity timers per guild
inactivity_timers: dict[int, asyncio.Task] = {}


async def leave_after_delay(
    guild: Guild, channel: TextChannel, delay: int = 180
) -> None:
    """
    Waits for `delay` seconds, then sends a message to the text channel
    and disconnects the bot from the voice channel if no activity has occurred.

    :param guild: Discord guild (server) object.
    :param channel: Text channel to send inactivity message in.
    :param delay: Time in seconds before leaving due to inactivity (default: 180).
    """
    await asyncio.sleep(delay)

    if guild.voice_client:  # Bot is still connected to a voice channel
        await channel.send(
            "No activity detected. Leaving the voice channel due to inactivity."
        )
        await guild.voice_client.disconnect()


def start_timer(guild: Guild, channel: TextChannel, delay: int = 180) -> None:
    """
    Starts or restarts an inactivity timer for the given guild.
    Cancels any existing timer for that guild to avoid overlaps.

    :param guild: Discord guild (server) object.
    :param channel: Text channel to send inactivity message in.
    :param delay: Time in seconds before leaving due to inactivity (default: 180).
    """
    if guild.id in inactivity_timers:
        inactivity_timers[guild.id].cancel()

    inactivity_timers[guild.id] = asyncio.create_task(
        leave_after_delay(guild, channel, delay)
    )
