"""
Discord.pyのページネーション機能を提供するユーティリティモジュール。

このモジュールはDiscordボット向けのページネーション表示機能を提供します。
複数のページを持つコンテンツを表示し、ユーザーが前後のページに移動できる
インタラクティブなUIを提供します。

Classes:
    EmbedField: Embedフィールド情報を保持するデータクラス
    PageSelectModal: ページ番号を入力するためのモーダル
    Pagination: 基本的なページネーション機能を提供するView
    ListPagination: リスト形式のコンテンツに特化したページネーション
"""

import discord
from discord.ext import commands
from typing import Protocol, Union, Callable, Optional
from dataclasses import dataclass
from math import ceil

__all__ = ("EmbedField", "PageSelectModal", "Pagination", "ListPagination", "ListPaginator", "ListEmbedRenderer", "FieldEmbedRenderer", "EmbedRenderer")


@dataclass
class EmbedField:
    """
    Embedフィールドの情報を保持するデータクラス

    Attributes:
        name (str): フィールドの名前
        value (str): フィールドの値
        inline (bool): フィールドをインライン表示するかどうか
    """

    name: str
    value: str
    inline: bool = False


class PageSelectModal(discord.ui.Modal):
    """
    ページ番号を入力するためのモーダルダイアログ

    特定のページに直接ジャンプするための入力フォームを提供します。
    """

    def __init__(self, page_view: "Pagination", title: str = "ページ選択"):
        """
        PageSelectModalを初期化します

        Args:
            page_view (Pagination): 親となるPaginationビュー
            title (str, optional): モーダルのタイトル。デフォルトは "ページ選択"
        """
        super().__init__(title=title)
        self.page_view = page_view

        self.page_input: discord.ui.TextInput = discord.ui.TextInput(
            label="ページ番号を入力",
            placeholder=f"1から{page_view.total_page_count}までの数字を入力",
            min_length=1,
            max_length=len(str(page_view.total_page_count)),
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        """
        モーダルが送信されたときに呼び出されるメソッド

        入力されたページ番号を検証し、有効な場合は該当ページに移動します。

        Args:
            interaction (discord.Interaction): 発生したインタラクション
        """
        try:
            page_number = int(self.page_input.value)
            if 1 <= page_number <= self.page_view.total_page_count:
                await self.page_view.go_to_page(interaction, page_number - 1)
            else:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        f"1から{self.page_view.total_page_count}までの数字を入力してください。",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"1から{self.page_view.total_page_count}までの数字を入力してください。",
                        ephemeral=True,
                    )
        except ValueError:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "有効な数字を入力してください。", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "有効な数字を入力してください。", ephemeral=True
                )


class Pagination(discord.ui.View):
    """
    Discord.pyのページネーション機能を提供するViewクラス

    複数のページを持つコンテンツをインタラクティブに表示するための基本クラスです。
    前後のページへの移動や、特定のページへの直接ジャンプなどの機能を提供します。
    """

    def __init__(self, *, timeout: int = 120) -> None:
        """
        Paginationを初期化します

        Args:
            timeout (int, optional): Viewのタイムアウト時間（秒）。デフォルトは120秒
        """
        super().__init__(timeout=timeout)

        self.pages: list[discord.Embed] = []  # ページのリスト
        self.ctx_or_interaction: commands.Context | discord.Interaction | None = (
            None  # コンテキストまたはインタラクション
        )
        self.message: discord.Message | discord.WebhookMessage | None = (
            None  # 送信されたメッセージ
        )
        self.current_page: int = 0  # 現在のページ番号（0から始まる）
        self.total_page_count: int = 0  # 総ページ数

    async def start(
        self,
        ctx_or_interaction: commands.Context | discord.Interaction,
        pages: list[discord.Embed],
    ):
        """
        ページネーションを開始します

        Args:
            ctx_or_interaction (commands.Context | discord.Interaction):
                コマンドコンテキストまたはインタラクション
            pages (list[discord.Embed]):
                表示するページのリスト（discord.Embedのリスト）
        """
        self.pages = pages
        self.total_page_count = len(pages)
        self.ctx_or_interaction = ctx_or_interaction

        self.add_button()

        if isinstance(ctx_or_interaction, commands.Context):
            self.message = await ctx_or_interaction.send(embed=self.pages[0], view=self)
        elif isinstance(ctx_or_interaction, discord.Interaction):
            msg = await ctx_or_interaction.followup.send(
                embed=self.pages[0], view=self, ephemeral=True
            )
            self.message = msg

        self.update_button_states()

    def add_button(self):
        """
        ページネーションに必要なボタンを追加します

        このメソッドでは以下のボタンを追加します：
        - 最初のページに移動するボタン
        - 前のページに移動するボタン
        - 現在のページ番号を表示するボタン（クリックでページ選択モーダルを表示）
        - 次のページに移動するボタン
        - 最後のページに移動するボタン
        """
        # ボタン定義
        self.first_page_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.primary, label="<<", custom_id="first_page"
        )
        self.previous_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.primary, label="<", custom_id="previous"
        )
        self.current_page_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.grey,
            label=f"1/{self.total_page_count}ページ",
            custom_id="current_page",
        )
        self.next_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.primary, label=">", custom_id="next"
        )
        self.last_page_button: discord.ui.Button = discord.ui.Button(
            style=discord.ButtonStyle.primary, label=">>", custom_id="last_page"
        )

        # ボタンのコールバックを設定
        self.first_page_button.callback = self.first_page_callback
        self.previous_button.callback = self.previous_button_callback
        self.current_page_button.callback = self.page_select_callback
        self.next_button.callback = self.next_button_callback
        self.last_page_button.callback = self.last_page_callback  # ボタンを追加
        self.add_item(self.first_page_button)
        self.add_item(self.previous_button)
        self.add_item(self.current_page_button)
        self.add_item(self.next_button)
        self.add_item(self.last_page_button)

    def update_button_states(self):
        """
        ページの状態に応じてボタンの有効/無効状態を更新します

        - 最初のページにいる場合、「最初へ」と「前へ」ボタンを無効化
        - 最後のページにいる場合、「次へ」と「最後へ」ボタンを無効化
        - ページ番号表示を更新
        """
        self.first_page_button.disabled = self.current_page == 0
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_page_count - 1
        self.last_page_button.disabled = self.current_page == self.total_page_count - 1
        self.current_page_button.label = (
            f"{self.current_page + 1}/{self.total_page_count}ページ"
        )

    async def go_to_page(self, interaction: discord.Interaction, page_number: int):
        """
        指定されたページ番号に移動します

        Args:
            interaction (discord.Interaction): 発生したインタラクション
            page_number (int): 移動先のページ番号（0から始まる）

        Note:
            有効なページ番号かどうかをチェックし、有効な場合のみ移動します
        """
        if 0 <= page_number < self.total_page_count:
            self.current_page = page_number
            self.update_button_states()
            try:
                await interaction.response.edit_message(
                    embed=self.pages[self.current_page], view=self
                )
            except discord.HTTPException:
                self.stop()

    async def first_page_callback(self, interaction: discord.Interaction):
        """
        最初のページに移動するボタンのコールバック

        Args:
            interaction (discord.Interaction): 発生したインタラクション
        """
        if not self._is_valid_user(interaction):
            return
        await self.go_to_page(interaction, 0)

    async def previous_button_callback(self, interaction: discord.Interaction):
        """
        前のページに移動するボタンのコールバック

        Args:
            interaction (discord.Interaction): 発生したインタラクション
        """
        if not self._is_valid_user(interaction):
            return
        await self.go_to_page(interaction, self.current_page - 1)

    async def page_select_callback(self, interaction: discord.Interaction):
        """
        ページ選択ボタンのコールバック（モーダルを表示）

        Args:
            interaction (discord.Interaction): 発生したインタラクション
        """
        if not self._is_valid_user(interaction):
            return
        modal = PageSelectModal(self)
        await interaction.response.send_modal(modal)

    async def next_button_callback(self, interaction: discord.Interaction):
        """
        次のページに移動するボタンのコールバック

        Args:
            interaction (discord.Interaction): 発生したインタラクション
        """
        if not self._is_valid_user(interaction):
            return
        await self.go_to_page(interaction, self.current_page + 1)

    async def last_page_callback(self, interaction: discord.Interaction):
        """
        最後のページに移動するボタンのコールバック

        Args:
            interaction (discord.Interaction): 発生したインタラクション
        """
        if not self._is_valid_user(interaction):
            return
        await self.go_to_page(interaction, self.total_page_count - 1)

    def _is_valid_user(self, interaction: discord.Interaction) -> bool:
        """
        インタラクションを行ったユーザーが有効かどうかをチェック

        ページネーションを開始したユーザーと同じユーザーかどうかを確認します。

        Args:
            interaction (discord.Interaction): チェック対象のインタラクション

        Returns:
            bool: 有効なユーザーの場合True、そうでない場合False
        """
        if isinstance(self.ctx_or_interaction, commands.Context):
            return interaction.user == self.ctx_or_interaction.author
        elif isinstance(self.ctx_or_interaction, discord.Interaction):
            return interaction.user == self.ctx_or_interaction.user
        return False

    async def on_timeout(self):
        """
        タイムアウト時の処理

        タイムアウトが発生した場合、全てのボタンを無効化し、
        メッセージを更新します。また、メモリリソースをクリーンアップします。
        """
        # 全てのボタンを無効化
        for item in self.children:
            item.disabled = True

        try:
            # メッセージを更新
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass

        # リソースクリーンアップ
        self.pages = None
        self.ctx_or_interaction = None
        self.message = None

class EmbedRenderer(Protocol):
    """Embed生成の責任を持つプロトコル"""
    def create_embed(self, items: list, page_info: dict) -> discord.Embed:
        ...


class ListEmbedRenderer:
    """リスト形式のEmbed生成器"""

    def __init__(
        self,
        title: str,
        color: discord.Color = discord.Color.green(),
        show_page_in_title: bool = True,
        item_formatter: Optional[Callable[[int, str], str]] = None
    ):
        self.title = title
        self.color = color
        self.show_page_in_title = show_page_in_title
        self.item_formatter = item_formatter or self._default_formatter

    def _default_formatter(self, index: int, item: str) -> str:
        return f"{index}. {item}"

    def create_embed(self, items: list[str], page_info: dict) -> discord.Embed:
        current = page_info["current"]
        total = page_info["total"]
        start_index = page_info["start_index"]

        title = self.title
        if self.show_page_in_title:
            title = f"{self.title} {current + 1}/{total}ページ"

        formatted_items = [
            self.item_formatter(start_index + i + 1, item)
            for i, item in enumerate(items)
        ]

        return discord.Embed(
            title=title,
            description="\n".join(formatted_items),
            color=self.color
        )


class FieldEmbedRenderer:
    """フィールド形式のEmbed生成器"""

    def __init__(
        self,
        title: str,
        color: discord.Color = discord.Color.green(),
        show_page_in_title: bool = True,
        footer_text: Optional[str] = None,
        footer_icon: Optional[str] = None
    ):
        self.title = title
        self.color = color
        self.show_page_in_title = show_page_in_title
        self.footer_text = footer_text
        self.footer_icon = footer_icon

    def create_embed(self, items: list[EmbedField], page_info: dict) -> discord.Embed:
        current = page_info["current"]
        total = page_info["total"]

        title = self.title
        if self.show_page_in_title:
            title = f"{self.title} {current + 1}/{total}ページ"

        embed = discord.Embed(title=title, color=self.color)

        for field in items:
            embed.add_field(
                name=field.name,
                value=field.value,
                inline=field.inline
            )

        if self.footer_text:
            embed.set_footer(text=self.footer_text, icon_url=self.footer_icon)

        return embed


class ListPaginator:
    """リスト形式のページネーション専用クラス"""

    def __init__(
        self,
        items: list[Union[str, EmbedField]],
        items_per_page: int = 10,
        renderer: Optional[EmbedRenderer] = None
    ):
        self.items = items
        self.items_per_page = items_per_page
        self.renderer = renderer or self._create_default_renderer()
        self.pages = self._create_pages()

    def _create_default_renderer(self) -> EmbedRenderer:
        """デフォルトのレンダラーを作成"""
        if all(isinstance(item, EmbedField) for item in self.items):
            return FieldEmbedRenderer(title="List")
        else:
            return ListEmbedRenderer(title="List")

    def _create_pages(self) -> list[discord.Embed]:
        """ページを作成"""
        pages = []
        total_pages = ceil(len(self.items) / self.items_per_page)

        for i in range(total_pages):
            start_idx = i * self.items_per_page
            end_idx = start_idx + self.items_per_page
            page_items = self.items[start_idx:end_idx]

            page_info = {
                "current": i,
                "total": total_pages,
                "start_index": start_idx
            }

            embed = self.renderer.create_embed(page_items, page_info)
            pages.append(embed)

        return pages


class ListPagination:
    """簡単なファクトリークラス"""

    @staticmethod
    async def start(
        ctx: commands.Context | discord.Interaction,
        items: list[Union[str, EmbedField]],
        *,
        title: str = "List",
        items_per_page: int = 10,
        timeout: int = 120,
        color: discord.Color = discord.Color.green(),
        show_page_in_title: bool = True,
        item_formatter: Optional[Callable[[int, str], str]] = None,
        footer_text: Optional[str] = None,
        footer_icon: Optional[str] = None
    ) -> None:
        """
        リスト形式のページネーションを開始

        Args:
            ctx: コンテキストまたはインタラクション
            items: 表示するアイテムのリスト
            title: ページのタイトル
            items_per_page: 1ページあたりのアイテム数
            timeout: タイムアウト時間
            color: Embedの色
            show_page_in_title: タイトルにページ番号を表示するか
            item_formatter: アイテムのフォーマット関数
            footer_text: フッターテキスト
            footer_icon: フッターアイコンURL
        """
        renderer: EmbedRenderer
        if all(isinstance(item, EmbedField) for item in items):
            renderer = FieldEmbedRenderer(
                title=title,
                color=color,
                show_page_in_title=show_page_in_title,
                footer_text=footer_text,
                footer_icon=footer_icon
            )
        else:
            renderer = ListEmbedRenderer(
                title=title,
                color=color,
                show_page_in_title=show_page_in_title,
                item_formatter=item_formatter
            )

        # ページネーターを作成
        paginator = ListPaginator(
            items=items,
            items_per_page=items_per_page,
            renderer=renderer
        )

        # ページが1つだけの場合は単純表示
        if len(paginator.pages) == 1:
            if isinstance(ctx, discord.Interaction):
                await ctx.followup.send(embed=paginator.pages[0])
            else:
                await ctx.send(embed=paginator.pages[0])
            return

        # 複数ページの場合はページネーション表示
        view = Pagination(timeout=timeout)
        await view.start(ctx, paginator.pages)
