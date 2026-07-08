import flet as ft

from components.login.body import Body


class LoginPage:
    """Login page class"""

    def __init__(self, page: ft.Page):
        """
        Initialize Login Page

        Args:
            page: The Flet page
        """
        self.page = page
        self.body = Body(page)

    def build(self):
        """Build and return the login page UI"""
        return ft.View(
            route="/login",
            controls=[
                self.body.build()
            ],
        )
