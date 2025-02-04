from enum import Enum
from typing import Any
import discord

__all__ = ("InteractionBucketType", "MemberBucketType")

class InteractionBucketType(Enum):
    default = 0
    user = 1
    guild = 2
    channel = 3
    member = 4
    category = 5
    role = 6

    def get_key(self, interaction: discord.Interaction) -> Any:
        if self is InteractionBucketType.user:
            return interaction.user.id
        elif self is InteractionBucketType.guild:
            return (interaction.guild or interaction.user).id
        elif self is InteractionBucketType.channel:
            return interaction.channel.id
        elif self is InteractionBucketType.member:
            return ((interaction.guild and interaction.guild.id), interaction.user.id)
        elif self is InteractionBucketType.category:
            return (getattr(interaction.channel, 'category', None) or interaction.channel).id
        elif self is InteractionBucketType.role:
            return (interaction.channel if isinstance(interaction.channel, discord.PrivateChannel) else interaction.user.top_role).id

    def __call__(self, interaction: discord.Interaction) -> Any:
        return self.get_key(interaction)

class MemberBucketType(Enum):
    default = 0
    user = 1
    guild = 2
    member = 3

    def get_key(self, member: discord.Member) -> Any:
        if self is MemberBucketType.user:
            return member.id
        elif self is MemberBucketType.guild:
            return (member.guild or member).id
        elif self is MemberBucketType.member:
            return ((member.guild and member.guild.id), member.id)

    def __call__(self, member: discord.Member) -> Any:
        return self.get_key(member)