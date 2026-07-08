import flet as ft

from components.module.loader_screen import LoaderScreen


class LoaderPage:
    """Loader screen for module loading"""

    def __init__(self, page: ft.Page):
        """Initialize loader screen
        Args:
            page: The Flet page
        """
        self.page = page
        self.loader = LoaderScreen(page)

    def build(self):
        return ft.View(
            route=self.page.route,
            controls=[
                self.loader.build()
            ],
            padding=0,
            bgcolor=ft.Colors.SURFACE,
        )
