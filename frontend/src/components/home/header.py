"""
Header component for the home
"""

import flet as ft

from components.home.user_menu import UserMenu
from components.module.header import APPBAR_HEIGHT_SMALL
from repository.storage import Storage


class Header:
    """Header AppBar component"""

    def __init__(self, page: ft.Page):
        """
        Initialize header

        Args:
            page: The Flet page
        """

        self.page = page
        self.storage: Storage = page.data["storage"]

        self.user_menu = UserMenu(page)

    def build(self):
        """Build and return the AppBar"""
        actions = []
        if self.user_menu:
            actions.append(self.user_menu.build())

        return ft.AppBar(
            title=ft.Text(
                self.storage.client_data.get_title(),
                color=ft.Colors.ON_SURFACE,
                size=16,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=ft.Colors.SURFACE,
            actions=actions,
            # M3 Small top app bar: start-aligned title, 64dp height
            # (issue #83) - kept on Home per that issue's own resolved
            # design decision (no "move title to a footer" M3 convention
            # exists; a bottom app bar holds navigation/FAB, not branding).
            center_title=False,
            toolbar_height=APPBAR_HEIGHT_SMALL,
        )
