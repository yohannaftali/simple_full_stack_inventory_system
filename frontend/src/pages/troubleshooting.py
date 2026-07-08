import flet as ft
from components.troubleshooting.header import Header
from components.troubleshooting.body import Body


class TroubleshootingPage:
    """Troubleshooting page class"""

    def __init__(self, page: ft.Page):
        """
        Initialize Troubleshooting Page

        Args:
            page: The Flet page
        """
        self.page = page

        self.header = Header(page)
        self.body = Body(page)

    def build(self):
        """Build and return the troubleshooting page UI"""
        return ft.View(
            route="/troubleshooting",
            controls=[
                self.header.build(),
                self.body.build(),
            ],
            spacing=0,
        )
