from typing import Dict, List

# Structure: {guild_id: {channel_id: [member_id_list]}}
channels_and_members: Dict[int, Dict[int, List[int]]] = {}


def add_member(guild_id: int, channel_id: int, member_id: int) -> None:
    """
    Add a member to a channel's member list in a guild.

    :param guild_id: ID of the Discord guild (server).
    :param channel_id: ID of the voice channel.
    :param member_id: ID of the member to add.
    """
    # Ensure the guild entry exists
    if guild_id not in channels_and_members:
        channels_and_members[guild_id] = {}

    # Ensure the channel entry exists within the guild
    if channel_id not in channels_and_members[guild_id]:
        channels_and_members[guild_id][channel_id] = []

    # Add member if not already in the channel's member list
    if member_id not in channels_and_members[guild_id][channel_id]:
        channels_and_members[guild_id][channel_id].append(member_id)


def remove_member(guild_id: int, channel_id: int, member_id: int) -> None:
    """
    Remove a member from a channel's member list in a guild.
    Cleans up empty channel and guild entries.

    :param guild_id: ID of the Discord guild (server).
    :param channel_id: ID of the voice channel.
    :param member_id: ID of the member to remove.
    """
    # Check if the guild and channel exist in the tracking dictionary
    if guild_id in channels_and_members and channel_id in channels_and_members[guild_id]:

        # Remove the member if they exist in the channel's member list
        if member_id in channels_and_members[guild_id][channel_id]:
            channels_and_members[guild_id][channel_id].remove(member_id)

            # If the channel has no members left, remove the channel entry
            if not channels_and_members[guild_id][channel_id]:
                del channels_and_members[guild_id][channel_id]

            # If the guild has no channels left, remove the guild entry
            if not channels_and_members[guild_id]:
                del channels_and_members[guild_id]
