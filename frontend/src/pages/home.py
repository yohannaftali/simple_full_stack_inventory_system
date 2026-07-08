import flet as ft

from components.home.header import Header
from components.home.body import Body


class HomePage:
    """Home page class"""

    def __init__(self, page: ft.Page):
        """
        Initialize Home Page

        Args:
            page: The Flet page
        """
        self.page = page

        self.header = Header(page)
        self.body = Body(page)

    def build(self):
        """Build and return the home page UI"""
        return ft.View(
            route="/home",
            controls=[
                self.header.build(),
                self.body.build(),
            ],
            spacing=0,
            padding=0,
            bgcolor=ft.Colors.SURFACE,
        )
