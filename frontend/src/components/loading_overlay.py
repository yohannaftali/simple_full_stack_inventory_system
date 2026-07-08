import flet as ft


class LoadingOverlay:
    """Full screen loading overlay with progress ring"""

    def __init__(self, page: ft.Page, message: str = "Loading..."):
        """
        Initialize loading overlay

        Args:
            page: The Flet page
            message: Loading message to display
        """
        self.page = page
        self.message = message
        self.overlay = None

    def build(self):
        """Build the loading overlay"""
        self.overlay = ft.Stack(
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.SURFACE)
                ),
                ft.Container(
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.ProgressRing(width=40, height=40),
                            ft.Text(
                                self.message,
                                color=ft.Colors.ON_SURFACE,
                                size=16
                            ),
                        ],
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                ),
            ],
            visible=False,
        )
        return self.overlay

    def show(self):
        """Show the loading overlay"""
        self.overlay.visible = True
        self.page.update()

    def hide(self):
        """Hide the loading overlay"""
        self.overlay.visible = False
        self.page.update()
