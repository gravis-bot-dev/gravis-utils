import zoneinfo
import discord
from typing import Union

__all__ = ("MessageAble","jst")

MessageAble = Union[discord.TextChannel, discord.Thread, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel]

jst = zoneinfo.ZoneInfo("Asia/Tokyo")