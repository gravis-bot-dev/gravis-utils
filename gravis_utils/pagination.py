import discord
from discord.ext import commands
from math import ceil

from typing import Sequence
from dataclasses import dataclass

__all__ = ("EmbedField", "PageSelectModal", "Pagination", "ListPagination")

@dataclass
class EmbedField():
    name: str
    value: str

class PageSelectModal(discord.ui.Modal):
    def __init__(self, page_view: 'Pagination', title: str = "ページ選択"):
        super().__init__(title=title)
        self.page_view = page_view

        self.page_input: discord.ui.TextInput = discord.ui.TextInput(
            label="ページ番号を入力",
            placeholder=f"1から{page_view.total_page_count}までの数字を入力",
            min_length=1,
            max_length=len(str(page_view.total_page_count))
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page_number = int(self.page_input.value)
            if 1 <= page_number <= self.page_view.total_page_count:
                await self.page_view.go_to_page(page_number - 1)
            else:
                if interaction.response.is_done():
                    await interaction.followup.send(f"1から{self.page_view.total_page_count}までの数字を入力してください。", ephemeral=True)
                else:
                    await interaction.response.send_message(f"1から{self.page_view.total_page_count}までの数字を入力してください。", ephemeral=True)
        except ValueError:
            if interaction.response.is_done():
                await interaction.followup.send("有効な数字を入力してください。", ephemeral=True)
            else:
                await interaction.response.send_message("有効な数字を入力してください。", ephemeral=True)



class Pagination(discord.ui.View):
    def __init__(
        self, *,
        timeout: int = 120
    ) -> None:
        super().__init__(timeout=timeout)

        self.pages: list[discord.Embed] | None = None
        self.ctx_or_interaction: commands.Context | discord.Interaction | None = None
        self.message: discord.Message | None = None
        self.current_page: int = 0
        self.total_page_count: int | None = None

    async def start(
        self,
        ctx_or_interaction: commands.Context | discord.Interaction,
        pages: list[discord.Embed]
    ):
        self.pages = pages
        self.total_page_count = len(pages)
        self.ctx_or_interaction = ctx_or_interaction

        self.add_button()

        if isinstance(ctx_or_interaction, commands.Context):
            self.message = await ctx_or_interaction.send(
                embed=self.pages[0],
                view=self
            )
        elif isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(
                embed=self.pages[0],
                view=self,
                ephemeral=True
            )
            self.message = await ctx_or_interaction.original_response()

        self.update_button_states()

    def add_button(self):
        # ボタン定義
        self.first_page_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="<<",
            custom_id="first_page"
        )
        self.previous_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="<",
            custom_id="previous"
        )
        self.current_page_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.grey,
            label=f"1/{self.total_page_count}ページ",
            custom_id="current_page"
        )
        self.next_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label=">",
            custom_id="next"
        )
        self.last_page_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label=">>",
            custom_id="last_page"
        )

        # ボタンのコールバックを設定
        self.first_page_button.callback = self.first_page_callback
        self.previous_button.callback = self.previous_button_callback
        self.current_page_button.callback = self.page_select_callback
        self.next_button.callback = self.next_button_callback
        self.last_page_button.callback = self.last_page_callback

        # ボタンを追加
        self.add_item(self.first_page_button)
        self.add_item(self.previous_button)
        self.add_item(self.current_page_button)
        self.add_item(self.next_button)
        self.add_item(self.last_page_button)

    def update_button_states(self):
        self.first_page_button.disabled = self.current_page == 0
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_page_count - 1
        self.last_page_button.disabled = self.current_page == self.total_page_count - 1
        self.current_page_button.label = f"{self.current_page + 1}/{self.total_page_count}ページ"

    async def go_to_page(self, page_number: int):
        if 0 <= page_number < self.total_page_count:
            self.current_page = page_number
            self.update_button_states()
            await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def first_page_callback(self, interaction: discord.Interaction):
        if not self._is_valid_user(interaction):
            return
        await self.go_to_page(0)

    async def previous_button_callback(self, interaction: discord.Interaction):
        if not self._is_valid_user(interaction):
            return
        await self.go_to_page(self.current_page - 1)

    async def page_select_callback(self, interaction: discord.Interaction):
        if not self._is_valid_user(interaction):
            return
        modal = PageSelectModal(self)
        await interaction.response.send_modal(modal)

    async def next_button_callback(self, interaction: discord.Interaction):
        if not self._is_valid_user(interaction):
            return
        await self.go_to_page(self.current_page + 1)

    async def last_page_callback(self, interaction: discord.Interaction):
        if not self._is_valid_user(interaction):
            return
        await self.go_to_page(self.total_page_count - 1)

    def _is_valid_user(self, interaction: discord.Interaction) -> bool:
        if isinstance(self.ctx_or_interaction, commands.Context):
            return interaction.user == self.ctx_or_interaction.author
        elif isinstance(self.ctx_or_interaction, discord.Interaction):
            return interaction.user == self.ctx_or_interaction.user
        return False

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)



class ListPagination(Pagination):
    def __init__(
        self, *,
        title: str,
        items_per_page: int = 10,
        timeout: int = 120
    ) -> None:
        super().__init__(timeout=timeout)
        self.base_title = title
        self.items_per_page = items_per_page

    def _create_embed(self, page_items: Sequence[str | EmbedField], current_page: int, total_pages: int) -> discord.Embed:
        if all(isinstance(item, EmbedField) for item in page_items):
            embed = discord.Embed(title=f"{self.base_title} {current_page + 1}/{total_pages}ページ")
            for field in page_items:
                embed.add_field(name={field.name}, value={field.value}, inline=False)
            return embed

        return discord.Embed(
            title=f"{self.base_title} {current_page + 1}/{total_pages}ページ",
            description="\n".join(f"{i + 1}. {item}" for i, item in enumerate(page_items, start=current_page * self.items_per_page))
        )

    def _create_embeds(self, items: Sequence[str | EmbedField]) -> list[discord.Embed]:
        total_pages = ceil(len(items) / self.items_per_page)
        embeds = []

        for i in range(total_pages):
            start_idx = i * self.items_per_page
            end_idx = start_idx + self.items_per_page
            page_items = items[start_idx:end_idx]
            embed = self._create_embed(page_items, i, total_pages)
            embeds.append(embed)

        return embeds

    @classmethod
    async def start_pagination(
        cls,
        ctx: commands.Context | discord.Interaction,
        items: Sequence[str | EmbedField],
        title: str,
        items_per_page: int = 10,
        timeout: int = 120
    ) -> None:
        view = cls(
            title=title,
            items_per_page=items_per_page,
            timeout=timeout
        )
        embeds = view._create_embeds(items)
        if len(embeds) > 1:
            await view.start(ctx, embeds)
            return

        if isinstance(ctx, discord.Interaction):
            await ctx.followup.send(embed=embeds[0])
        else:
            await ctx.send(embed=embeds[0])