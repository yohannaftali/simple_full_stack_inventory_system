"""
Header component for the home
"""

import flet as ft

from repository.storage import Storage
from components.home.user_menu import UserMenu


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
                color=ft.Colors.ON_PRIMARY),
            bgcolor=ft.Colors.PRIMARY,
            actions=actions,
            center_title=True
        )
