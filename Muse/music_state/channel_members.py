from collections import defaultdict
from typing import Dict, List

# Structure: {guild_id: {channel_id: [member_id_list]}}
channels_and_members: Dict[int, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))


def add_member(guild_id: int, channel_id: int, member_id: int) -> None:
    """Add a member to a channel's member list in a guild."""
    if member_id not in channels_and_members[guild_id][channel_id]:
        channels_and_members[guild_id][channel_id].append(member_id)


def remove_member(guild_id: int, channel_id: int, member_id: int) -> None:
    """Remove a member from a channel's member list in a guild."""
    channel_members = channels_and_members[guild_id][channel_id]
    
    if member_id in channel_members:
        channel_members.remove(member_id)

        # Clean up empty channel and guild entries
        if not channel_members:
            del channels_and_members[guild_id][channel_id]
        if not channels_and_members[guild_id]:
            del channels_and_members[guild_id]
