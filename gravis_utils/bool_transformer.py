import discord
from discord import app_commands

__all__ = ("BoolTransformer")

class BoolTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> bool:
        return value == "有効"

    async def autocomplete(self, interaction: discord.Interaction, current: str):
        options = ["有効", "無効"]
        return [app_commands.Choice(name=option, value=option) for option in options if current in option]