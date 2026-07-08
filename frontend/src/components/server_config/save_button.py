"""Save Button Component for Server Config"""

import flet as ft


class SaveButton:
    """
    Save Button
    """

    def __init__(self, on_click_callback):
        """
        Initialize Save Button

        Args:
            on_click_callback: on_click callback
        """
        self.on_click_callback = on_click_callback

    def build(self):
        return ft.Button(
            content="Save Configuration",
            width=300,
            height=50,
            on_click=self.on_click_callback,
            icon=ft.Icons.SAVE,
            bgcolor=ft.Colors.PRIMARY,
            color=ft.Colors.ON_PRIMARY,
            style=ft.ButtonStyle(
                overlay_color=ft.Colors.SECONDARY
            )
        )
