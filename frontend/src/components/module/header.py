"""
Header component for the module
"""

import flet as ft

from components.home.user_menu import UserMenu


class ModuleHeader:
    """Header AppBar component"""

    def __init__(self, page: ft.Page, screen_label: str = "Module"):
        """
        Initialize header

        Args:
            page: The Flet page
            screen_label: str
        """
        self.page = page

        # Material 3 top app bars use a neutral surface color, not primary -
        # unlike the home page's own AppBar (components/home/header.py),
        # which still uses primary.
        self.user_menu = UserMenu(page, icon_color=ft.Colors.ON_SURFACE)
        self.title = screen_label

    def build(self):
        """Build and return the AppBar"""
        actions = [
            ft.IconButton(
                icon=ft.Icons.SEARCH,
                icon_color=ft.Colors.ON_SURFACE,
                icon_size=24,
                tooltip="Home",
                on_click=self.on_home_click,
            )
        ]
        if self.user_menu:
            actions.append(self.user_menu.build())

        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.ON_SURFACE,
                icon_size=24,
                # leading_width below only bounds the slot's *width* - its
                # height still stretches to the toolbar's full height
                # (56px default), so the button's own hover/splash ripple
                # fills that taller box unless explicitly pinned to match
                # the action icons' tightly-wrapped 48x48 footprint.
                width=48,
                height=48,
                tooltip="Back",
                on_click=self.on_click,
            ),
            # AppBar.leading otherwise gets a 56px-wide slot by default
            # (Flutter's kToolbarHeight), noticeably wider than the ~48px
            # tap-target box the action icons naturally get - same icon_size,
            # but the back button's whole clickable/visual footprint ends up
            # bigger. Match it to the standard Material icon-button size.
            leading_width=48,
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
        if hasattr(self.page, 'banner') and self.page.banner:
            self.page.banner.open = False
            self.page.update()

        history = []
        if hasattr(self.page, "data") and isinstance(self.page.data, dict):
            history = self.page.data.get("module_history", [])
        if history:
            history.pop()
        if history:
            prev_module, prev_screen = history[-1]
            self.page.data["module_history"] = history
            self.page.run_task(self.page.push_route, f"/modules/{prev_module}/{prev_screen}")
        else:
            self.page.run_task(self.page.push_route, "/home")

    def on_home_click(self, e):
        """Navigate back to home"""
        if hasattr(self.page, 'banner') and self.page.banner:
            self.page.banner.open = False
            self.page.update()

        self.page.run_task(self.page.push_route, "/home")
