# Structure: {guild_id: {channel_id: [member_list]}}
channels_and_members = {}

def add_member(guild_id, channel_id, member_id):
    # If the guild doesn't exist in the dictionary yet, create it
    if guild_id not in channels_and_members:
        channels_and_members[guild_id] = {}

    # If the channel doesn't exist inside that guild yet, create it
    if channel_id not in channels_and_members[guild_id]:
        channels_and_members[guild_id][channel_id] = []

    # If the member is not already in the channel's list, add them
    if member_id not in channels_and_members[guild_id][channel_id]:
        channels_and_members[guild_id][channel_id].append(member_id)


def remove_member(guild_id, channel_id, member_id):
    # Check if the guild and channel exist first
    if guild_id in channels_and_members and channel_id in channels_and_members[guild_id]:

        # Remove member if they exist
        if member_id in channels_and_members[guild_id][channel_id]:
            channels_and_members[guild_id][channel_id].remove(member_id)

            # If channel is now empty, remove channel entry
            if not channels_and_members[guild_id][channel_id]:
                del channels_and_members[guild_id][channel_id]

            # If guild has no channels left, remove guild entry
            if not channels_and_members[guild_id]:
                del channels_and_members[guild_id]

