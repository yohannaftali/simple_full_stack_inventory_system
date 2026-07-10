"""
Header component for the modal
"""

import flet as ft


class ModalHeader:
    """Header AppBar component"""

    def __init__(self, page: ft.Page, screen_label: str = "Modal"):
        """
        Initialize header

        Args:
            page: The Flet page
            screen_label: str
        """
        self.page = page
        self.title = screen_label

    def build(self):
        """Build and return the AppBar"""
        actions = [
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_color=ft.Colors.ON_SURFACE,
                tooltip="Close",
                on_click=self.on_click,
            )
        ]

        return ft.AppBar(
            title=ft.Text(
                self.title,
                color=ft.Colors.ON_SURFACE,
                size=16
            ),
            bgcolor=ft.Colors.SURFACE,
            actions=actions,
            center_title=True,
            elevation=0,
            elevation_on_scroll=0,
            shadow_color=ft.Colors.SHADOW,
        )

    def set_title(self, title: str):
        """Set the title of the AppBar"""
        self.title = title

    def on_click(self, e):
        """Navigate back within module screens or to home if history exhausted."""
        # Close any open banners
        if hasattr(self.page, 'banner') and self.page.banner:
            self.page.banner.open = False
            self.page.update()

        history = []
        if hasattr(self.page, "data") and isinstance(self.page.data, dict):
            history = self.page.data.get("module_history", [])
        if history:
            prev_module, prev_screen = history[-1]
            self.page.data["module_history"] = history
            self.page.run_task(self.page.push_route, f"/modules/{prev_module}/{prev_screen}")
        else:
            self.page.run_task(self.page.push_route, "/home")
