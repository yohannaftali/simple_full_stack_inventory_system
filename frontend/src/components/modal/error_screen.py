import flet as ft


class ErrorScreen:
    """Error screen for failed modal loading"""

    def __init__(self, modal_path: str, error: str):
        self.modal_path = modal_path
        self.error = error

    def build(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.ERROR_OUTLINE,
                        size=64,
                        color=ft.Colors.ERROR,
                    ),
                    ft.Text(
                        "Modal Not Found",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    ft.Text(
                        f"Path: {self.modal_path}",
                        size=14,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    ft.Text(
                        f"Error: {self.error}",
                        size=12,
                        color=ft.Colors.ERROR,
                        italic=True,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=40,
            alignment=ft.Alignment.CENTER,
        )
