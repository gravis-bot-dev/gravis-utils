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
from math import ceil

from typing import Sequence
from dataclasses import dataclass

__all__ = ("EmbedField", "PageSelectModal", "Pagination", "ListPagination")


@dataclass
class EmbedField:
    """
    Embedフィールドの情報を保持するデータクラス

    Attributes:
        name (str): フィールドの名前
        value (str): フィールドの値
    """

    name: str
    value: str


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

        self.pages: list[discord.Embed] | None = None  # ページのリスト
        self.ctx_or_interaction: commands.Context | discord.Interaction | None = (
            None  # コンテキストまたはインタラクション
        )
        self.message: discord.Message | discord.WebhookMessage | None = (
            None  # 送信されたメッセージ
        )
        self.current_page: int = 0  # 現在のページ番号（0から始まる）
        self.total_page_count: int | None = None  # 総ページ数

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
            self.message = await ctx_or_interaction.followup.send(
                embed=self.pages[0], view=self, ephemeral=True
            )

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


class ListPagination(Pagination):
    """
    リスト形式のコンテンツをページング表示するための拡張クラス

    テキストのリストやEmbedFieldのリストを簡単にページング表示するための
    ユーティリティクラスです。自動的にページを生成し、適切な形式で表示します。
    """

    def __init__(
        self,
        *,
        title: str,
        items_per_page: int = 10,
        timeout: int = 120,
        embed_color: discord.Color = discord.Color.green(),
    ) -> None:
        """
        ListPaginationを初期化します

        Args:
            title (str): ページのタイトル
            items_per_page (int, optional): 1ページあたりのアイテム数。デフォルトは10
            timeout (int, optional): Viewのタイムアウト時間（秒）。デフォルトは120秒
            embed_color (discord.Color, optional): Embedの色。デフォルトは緑色
        """
        super().__init__(timeout=timeout)
        self.base_title = title
        self.items_per_page = items_per_page
        self.color = embed_color

    def _create_embed(
        self,
        page_items: Sequence[str | EmbedField],
        current_page: int,
        total_pages: int,
        is_show_page_in_title: bool = True,
    ) -> discord.Embed:
        """
        ページアイテムからEmbedを作成します

        Args:
            page_items (Sequence[str | EmbedField]):
                ページに表示するアイテムのリスト。文字列またはEmbedFieldのシーケンス
            current_page (int): 現在のページ番号（0から始まる）
            total_pages (int): 総ページ数
            is_show_page_in_title (bool, optional):
                タイトルにページ番号を表示するかどうか。デフォルトはTrue

        Returns:
            discord.Embed: 作成されたEmbed

        Note:
            アイテムの種類（文字列またはEmbedField）に応じて適切な形式のEmbedを作成します
        """
        if all(isinstance(item, EmbedField) for item in page_items):
            # EmbedFieldの場合はフィールド形式で表示
            if is_show_page_in_title:
                embed = discord.Embed(
                    title=f"{self.base_title} {current_page + 1}/{total_pages}ページ",
                    color=self.color,
                )
            else:
                embed = discord.Embed(title=self.base_title)
            for field in page_items:
                embed.add_field(name={field.name}, value={field.value}, inline=False)
            embed.set_footer(
                icon_url=self.ctx_or_interaction.client.user.avatar.url,
                text=self.ctx_or_interaction.client.user.display_name,
            )
            return embed

        # 文字列の場合はリスト形式で表示
        return discord.Embed(
            title=f"{self.base_title} {current_page + 1}/{total_pages}ページ",
            description="\n".join(
                f"{i + 1}. {item}"
                for i, item in enumerate(
                    page_items, start=current_page * self.items_per_page
                )
            ),
        )

    def _create_embeds(
        self, items: Sequence[str | EmbedField], is_show_page_in_title: bool = True
    ) -> list[discord.Embed]:
        """
        アイテムリストから複数のEmbedページを作成します

        Args:
            items (Sequence[str | EmbedField]):
                ページング表示するアイテムのリスト。文字列またはEmbedFieldのシーケンス
            is_show_page_in_title (bool, optional):
                タイトルにページ番号を表示するかどうか。デフォルトはTrue

        Returns:
            list[discord.Embed]: 作成されたEmbedのリスト

        Note:
            アイテムを指定した数ずつに分割し、各ページのEmbedを作成します
        """
        total_pages = ceil(len(items) / self.items_per_page)
        embeds = []

        for i in range(total_pages):
            start_idx = i * self.items_per_page
            end_idx = start_idx + self.items_per_page
            page_items = items[start_idx:end_idx]
            embed = self._create_embed(
                page_items, i, total_pages, is_show_page_in_title
            )
            embeds.append(embed)

        return embeds

    @classmethod
    async def start_pagination(
        cls,
        ctx: commands.Context | discord.Interaction,
        items: Sequence[str | EmbedField],
        title: str,
        items_per_page: int = 10,
        timeout: int = 120,
        embed_color: discord.Color = discord.Color.green(),
    ) -> None:
        """
        リスト形式のページネーションを開始します

        このクラスメソッドは、リスト形式のデータをページング表示するための
        便利なエントリポイントです。内部でListPaginationインスタンスを作成し、
        適切な形式でページを表示します。

        Args:
            ctx (commands.Context | discord.Interaction):
                コマンドコンテキストまたはインタラクション
            items (Sequence[str | EmbedField]):
                表示するアイテムのリスト。文字列またはEmbedFieldのシーケンス
            title (str):
                ページのタイトル
            items_per_page (int, optional):
                1ページあたりのアイテム数。デフォルトは10
            timeout (int, optional):
                Viewのタイムアウト時間（秒）。デフォルトは120秒
            embed_color (discord.Color, optional):
                Embedの色。デフォルトは緑色

        Note:
            - アイテム数が少なく1ページに収まる場合は、ページネーションなしで表示します
            - 複数ページある場合は、インタラクティブなページネーションを表示します

        Example:
            ```python
            # 文字列リストの場合
            items = ["アイテム1", "アイテム2", "アイテム3", ...]
            await ListPagination.start_pagination(ctx, items, "アイテム一覧")

            # EmbedFieldリストの場合
            fields = [
                EmbedField(name="項目1", value="説明1"),
                EmbedField(name="項目2", value="説明2"),
                ...
            ]
            await ListPagination.start_pagination(ctx, fields, "詳細情報")
            ```
        """
        view = cls(
            title=title,
            items_per_page=items_per_page,
            timeout=timeout,
            embed_color=embed_color,
        )
        embeds = view._create_embeds(items)
        if len(embeds) > 1:
            # 複数ページある場合はページネーション表示
            await view.start(ctx, embeds)
            return

        # 1ページだけの場合は単純に表示
        if isinstance(ctx, discord.Interaction):
            await ctx.followup.send(embed=embeds[0])
        else:
            await ctx.send(embed=embeds[0])
