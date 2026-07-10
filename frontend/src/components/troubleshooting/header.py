"""
Header component for the troubleshooting page
"""

import flet as ft


class Header:
    """Header AppBar component"""

    def __init__(self, page: ft.Page):
        """
        Initialize header

        Args:
            page: The Flet page
        """
        self.page = page

    def build(self):
        """Build and return the AppBar"""
        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.ON_SURFACE,
                tooltip="Back",
                on_click=self.on_back_click,
            ),
            title=ft.Text("Troubleshooting", color=ft.Colors.ON_SURFACE),
            bgcolor=ft.Colors.SURFACE,
            center_title=True,
            elevation=0,
            elevation_on_scroll=0,
            shadow_color=ft.Colors.SHADOW,
        )

    def on_back_click(self, e):
        """Navigate back to home if logged in, otherwise login"""
        storage = self.page.data.get("storage") if hasattr(self.page, "data") else None
        if storage and storage.client_data.is_active():
            self.page.run_task(self.page.push_route, "/home")
        else:
            self.page.run_task(self.page.push_route, "/login")
