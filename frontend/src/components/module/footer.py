"""
Footer component for the module
"""

import flet as ft
from repository.storage import Storage


class ModuleFooter:
    """Footer component"""

    def __init__(self, page: ft.Page, controls: list | None):
        """
        Initialize footer

        Args:
            page: The Flet page
        """
        self.page = page
        self.controls = controls

        self.storage: Storage = page.data.get("storage")

    def build(self):
        """Build and return the footer component"""
        self.controls = self.controls if self.controls is not None else self.default_footer()

        return ft.Container(
            content=ft.Row(
                controls=self.controls,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            # Material 3 chrome uses a neutral surface color, not primary -
            # matches components/module/header.py's top bar.
            bgcolor=ft.Colors.SURFACE,
            padding=5,
        )

    def default_footer(self):
        footer_text = self.storage.client_data.get_footer()
        controls = [
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.APP_REGISTRATION,
                            color=ft.Colors.ON_SURFACE, size=10),
                    ft.Text(
                        footer_text,
                        size=8,
                        color=ft.Colors.ON_SURFACE,
                    )
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
                tight=True,
            ),
        ]

        # Web has no Server Configuration screen (issue #36) - the address
        # is always fixed via FRONTEND_DEFAULT_SERVER_URL, so showing it
        # here has no value. Desktop/mobile keep it, since it's genuinely
        # user-configurable there.
        if not bool(getattr(self.page, "web", False)):
            controls.append(
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DATASET,
                                color=ft.Colors.ON_SURFACE, size=10),
                        ft.Text(
                            self.storage.server_url.get(),
                            size=8,
                            color=ft.Colors.ON_SURFACE,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5,
                    tight=True,
                )
            )

        return controls
