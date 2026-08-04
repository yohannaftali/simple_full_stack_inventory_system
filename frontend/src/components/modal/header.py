"""
Header component for the modal
"""

import flet as ft

from components.button import TOUCH_TARGET_SIZE
from components.module.header import APPBAR_HEIGHT_SMALL


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
        # Standard back arrow, not a Close (X) icon (issue #83) - modals
        # already navigate back through the same module_history stack a
        # module screen's own back button uses (see on_click below), so a
        # back arrow reads correctly rather than implying a distinct
        # "dismiss dialog" action. No subtitle line here (unlike
        # ModuleHeader) - a modal's own identity (e.g. "password"/"totp")
        # is just a raw route slug, not a resolved display name, and
        # showing it above the existing title (e.g. "Change Password")
        # would read as redundant rather than orienting.
        actions = [
            ft.IconButton(
                icon=ft.Icons.HOME,
                icon_color=ft.Colors.ON_SURFACE,
                icon_size=24,
                width=TOUCH_TARGET_SIZE,
                height=TOUCH_TARGET_SIZE,
                tooltip="Home",
                on_click=self.on_home_click,
            )
        ]

        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.ON_SURFACE,
                icon_size=24,
                width=TOUCH_TARGET_SIZE,
                height=TOUCH_TARGET_SIZE,
                tooltip="Back",
                on_click=self.on_click,
            ),
            leading_width=TOUCH_TARGET_SIZE,
            title=ft.Text(
                self.title,
                color=ft.Colors.ON_SURFACE,
                size=16,
                weight=ft.FontWeight.W_500,
            ),
            center_title=False,
            toolbar_height=APPBAR_HEIGHT_SMALL,
            bgcolor=ft.Colors.SURFACE,
            actions=actions,
            elevation=0,
            elevation_on_scroll=0,
            shadow_color=ft.Colors.SHADOW,
        )

    def set_title(self, title: str):
        """Set the title of the AppBar"""
        self.title = title

    def on_home_click(self, e):
        """Navigate to home"""
        if hasattr(self.page, "banner") and self.page.banner:
            self.page.banner.open = False
            self.page.update()

        self.page.data["module_history"] = []
        self.page.run_task(self.page.push_route, "/home")

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
            prev_module, prev_screen, prev_record_id = history[-1]
            self.page.data["module_history"] = history
            route = f"/modules/{prev_module}/{prev_screen}"
            if prev_record_id is not None:
                route += f"/{prev_record_id}"
            self.page.run_task(self.page.push_route, route)
        else:
            self.page.run_task(self.page.push_route, "/home")
