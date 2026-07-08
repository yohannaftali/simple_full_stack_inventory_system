import flet as ft
from components.list.layout import Layout
from components.list.tiles import Tiles


class Body:
    def __init__(self, page: ft.Page, layout: Layout, tiles: Tiles, on_scroll_end=None):
        self.page = page
        self.layout = layout
        self.tiles = tiles
        self.list_view: ft.ListView | None = None
        self.body_container: ft.Container | None = None
        self.loading_indicator: ft.ProgressRing | None = None
        self.loading_overlay: ft.Container | None = None
        self.on_scroll_end = on_scroll_end
        self.is_loading = False

    def build(self):
        self.list_view = ft.ListView(
            controls=self.tiles.build(),
            spacing=5,
            padding=10,
            expand=True,
            auto_scroll=False,
            on_scroll=self._on_scroll
        )

        # Loading indicator overlay
        self.loading_indicator = ft.ProgressRing(visible=False)
        self.loading_overlay = ft.Container(
            content=ft.Column(
                controls=[
                    self.loading_indicator,
                    ft.Text("Loading...", visible=False)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.Alignment.CENTER,
            visible=False,
            expand=True
        )

        self.body_container = ft.Container(
            content=ft.Stack(
                controls=[
                    self.list_view,
                    self.loading_overlay
                ]
            ),
            expand=True,
        )
        return self.body_container

    def _on_scroll(self, e: ft.OnScrollEvent):
        """Detect when user scrolls near bottom"""
        if self.is_loading or self.on_scroll_end is None:
            return

        # Check if we have valid scroll extent
        if e.max_scroll_extent is None or e.max_scroll_extent <= 0:
            return

        # Load more when scrolled to 90% or more
        scroll_percentage = e.pixels / e.max_scroll_extent if e.max_scroll_extent > 0 else 0

        if scroll_percentage >= 0.9:
            print(
                f"Scroll triggered: {scroll_percentage:.2%} - Loading more...")
            self.is_loading = True
            self.on_scroll_end()
            self.is_loading = False

    def update(self):
        print("Body.update")
        if self.list_view is not None:
            self.list_view.controls = self.tiles.build()
            self.list_view.update()
            print("list updated")

    def show_loading(self):
        """Show loading indicator"""
        if self.loading_overlay is not None:
            self.loading_overlay.visible = True
            self.loading_indicator.visible = True
            if self.body_container is not None:
                self.body_container.update()

    def hide_loading(self):
        """Hide loading indicator"""
        if self.loading_overlay is not None:
            self.loading_overlay.visible = False
            self.loading_indicator.visible = False
            if self.body_container is not None:
                self.body_container.update()
