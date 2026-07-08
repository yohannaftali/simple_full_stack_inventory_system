import flet as ft
from components.server_config.header import Header
from components.server_config.body import Body


class ServerConfigPage:
    """Configuration page class"""

    def __init__(self, page: ft.Page):
        """
        Initialize Server Config Page

        Args:
            page: The Flet page
        """
        self.page = page

        self.header = Header(page)
        self.body = Body(page)

    def build(self):
        """Build and return the config page UI"""
        return ft.View(
            route="/server_config",
            controls=[
                self.header.build(),
                self.body.build()
            ],
            spacing=0,
        )
