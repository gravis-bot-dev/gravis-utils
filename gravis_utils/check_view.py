import discord
from typing import Callable

__all__ = ("CheckMessage")

class CheckMessage(discord.ui.View):
    def __init__(
        self, *,
        timeout: int = 120
    ) -> None:
        super().__init__(timeout=timeout)
        self.message: discord.WebhookMessage

    async def start(self, interaction: discord.Interaction, check_msg: str, confirm_callback: Callable) -> None:
        await self.add_button()
        self.confirm_button_callback = confirm_callback

        if interaction.response.is_done():
            self.message = await interaction.followup.send(check_msg, view=self)
        else:
            await interaction.response.defer()
            self.message = await interaction.followup.send(check_msg, view=self)

    async def add_button(self) -> None:
        self.confirm_button: discord.ui.Button = discord.ui.Button(style=discord.ButtonStyle.success, label="実行", custom_id="confirm")
        self.cancel_button: discord.ui.Button = discord.ui.Button(style=discord.ButtonStyle.danger, label="キャンセル", custom_id="cancel")

        self.confirm_button.callback = self.confirm_button_callback
        self.cancel_button.callback = self.cancel_button_callback

    async def cancel_button_callback(self, interaction: discord.Interaction) -> None:
        await self.message.edit(content="キャンセルしました。\n（このメッセージは数秒後に削除されます）", view=None)
        await self.message.delete(delay=5.0)