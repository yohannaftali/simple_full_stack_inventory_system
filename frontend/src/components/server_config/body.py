"""
Body component for the server configuration
"""
import time

import flet as ft

from repository.storage import Storage
from components.server_config.save_button import SaveButton


class Body:
    """Body component"""

    def __init__(self, page: ft.Page):
        """
        Initialize body

        Args:
            page: The Flet page
        """
        self.page = page
        self.storage: Storage = page.data["storage"]
        self.server_url_field = ft.TextField(
            label="Server URL",
            hint_text="Enter base server URL (e.g., http://localhost:8000)",
            prefix_icon=ft.Icons.CLOUD,
            border_radius=10,
            autofocus=True,
            width=350,
            value=self.storage.server_url.get(),
        )

        self.save_button = SaveButton(on_click_callback=self.on_save_click)

        self.success_message = ft.Text(
            "",
            color=ft.Colors.GREEN_400,
            size=14,
            visible=False,
        )

    def build(self):
        """Build and return the body column"""
        controls = [
            self.server_url_field,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            self.success_message,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            self.save_button.build()
        ]
        return ft.SafeArea(
            content=ft.Container(
                content=ft.Column(
                    controls=controls,
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=20,
            ),
            expand=True,
        )

    def on_save_click(self, e):
        """Handle save button click"""
        server_url = self.server_url_field.value

        if not server_url:
            self.success_message.value = "Please enter a server URL"
            self.success_message.color = ft.Colors.RED_400
            self.success_message.visible = True
            self.page.update()
            return

        # Save to storage storage
        self.storage.server_url.set(server_url)

        # Show success message
        self.success_message.value = "Configuration saved successfully!"
        self.success_message.color = ft.Colors.GREEN_400
        self.success_message.visible = True
        self.page.update()

        # Navigate back to login page after a short delay
        time.sleep(1)
        self.page.run_task(self.page.push_route, "/login")
