"""Troubleshooting Button Component for Login page"""

import flet as ft


class TroubleshootingButton:
    """
    Troubleshooting Button
    """

    def __init__(self, on_click_callback):
        """
        Initialize Troubleshooting Button

        Args:
            on_click_callback: on_click callback
        """
        self.on_click_callback = on_click_callback

    def build(self):
        return ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.BUILD,
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text(
                        "Troubleshooting",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=5,
                tight=True,
            ),
            on_click=self.on_click_callback,
        )
