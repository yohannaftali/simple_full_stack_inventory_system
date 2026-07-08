import flet as ft


class LoaderScreen:
    """Loader screen for module loading"""

    def __init__(self, page: ft.Page):
        """Initialize loader screen
        Args:
            page: The Flet page
        """
        self.page = page

    def build(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.ProgressRing(),
                    ft.Text("Loading...", size=16, color=ft.Colors.ON_SURFACE),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.Alignment.CENTER,
        )
