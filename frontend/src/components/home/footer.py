"""
Footer component for the application
"""

import flet as ft
from repository.storage import Storage


class Footer:
    """Footer component"""

    def __init__(self, page: ft.Page):
        """
        Initialize footer

        Args:
            session: Storage instance
        """
        self.page = page

        self.storage: Storage = page.data.get("storage")

    def build(self):
        """Build and return the footer container"""
        return ft.Container(
            content=ft.Row(
                controls=self.default_footer(),
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=ft.Colors.PRIMARY,
            padding=5,
        )

    def default_footer(self):
        footer_text = self.storage.client_data.get_footer()
        controls = [
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.APP_REGISTRATION,
                            color=ft.Colors.ON_PRIMARY, size=10),
                    ft.Text(
                        footer_text,
                        size=8,
                        color=ft.Colors.ON_PRIMARY,
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
                                color=ft.Colors.ON_PRIMARY, size=10),
                        ft.Text(
                            self.storage.server_url.get(),
                            size=8,
                            color=ft.Colors.ON_PRIMARY,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5,
                    tight=True,
                )
            )

        return controls
