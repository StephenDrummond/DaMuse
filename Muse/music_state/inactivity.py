import asyncio
from discord import TextChannel, VoiceChannel

# Stores active inactivity timers per guild
inactivity_timers: dict[int, asyncio.Task] = {}



async def leave_after_delay(guild, channel: TextChannel, delay: int = 180):
    """
    Waits for `delay` seconds, then sends a message to the channel
    and disconnects the bot if no activity has occurred.
    """
    await asyncio.sleep(delay)

    if guild.voice_client:  # Bot is still in the channel
        await channel.send("No activity detected. Leaving the voice channel due to inactivity.")
        await guild.voice_client.disconnect()


def start_timer(guild, channel: TextChannel, delay: int = 180):
    """
    Starts or restarts an inactivity timer for the given guild.
    Cancels any existing timer for that guild.
    """
    if guild.id in inactivity_timers:
        inactivity_timers[guild.id].cancel()

    inactivity_timers[guild.id] = asyncio.create_task(leave_after_delay(guild, channel, delay))