"""Login Button Component for Login"""

import flet as ft


class LoginButton:
    """
    Login Button
    """

    def __init__(self, on_click_callback):
        """
        Initialize Login Button

        Args:
            on_click_callback: on_click callback
        """
        self.on_click_callback = on_click_callback

    def build(self):
        return ft.Button(
            content="Login",
            width=300,
            height=50,
            on_click=self.on_click_callback,
            icon=ft.Icons.LOGIN,
            bgcolor=ft.Colors.PRIMARY,
            color=ft.Colors.ON_PRIMARY,
            style=ft.ButtonStyle(
                overlay_color=ft.Colors.SECONDARY
            )
        )
