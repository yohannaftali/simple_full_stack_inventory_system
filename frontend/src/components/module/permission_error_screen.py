import flet as ft


class PermissionErrorScreen:
    """Permission error screen for failed module loading"""

    def __init__(self, module_path: str, error: str):
        """Initialize permission error screen
        Args:
            module_path: String
            error: String
        """
        self.module_path = module_path
        self.error = error

    def build(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.LOCK_CLOCK_OUTLINED,
                        size=64,
                        color=ft.Colors.ERROR,
                    ),
                    ft.Text(
                        "Permission Denied",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    ft.Text(
                        f"Path: {self.module_path}",
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
