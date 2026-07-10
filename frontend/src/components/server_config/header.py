"""
Header component for the server config
"""

import flet as ft


class Header:
    """Header AppBar component"""

    def __init__(self, page: ft.Page):
        """
        Initialize header

        Args:
            page: The Flet page
            session: Storage instance
        """
        self.page = page

    def build(self):
        """Build and return the AppBar"""
        actions = []

        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.ON_SURFACE,
                tooltip="Back to Login",
                on_click=self.on_back_click,
            ),
            title=ft.Text("Server Configuration", color=ft.Colors.ON_SURFACE),
            bgcolor=ft.Colors.SURFACE,
            actions=actions,
            center_title=True,
            elevation=0,
            elevation_on_scroll=0,
            shadow_color=ft.Colors.SHADOW,
        )

    def on_back_click(self, e):
        """Navigate back to login"""
        self.page.run_task(self.page.push_route, "/login")
