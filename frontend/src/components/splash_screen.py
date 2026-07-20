import flet as ft


class SplashScreen:
    """Full-screen splash view with a progress bar, shown at app startup
    while persisted storage loads and modules/modals preload."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.status_text = ft.Text(
            "Starting...", size=13, color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.progress_bar = ft.ProgressBar(width=220, value=0)
        # Dev-only escape hatch: if a hot-reloaded `flet run -r` session
        # gets stuck here (stale module/cache state from a previous code
        # version), this lets the user force a fresh preload + navigation
        # retry without restarting the whole process. Hidden until
        # `show_reload_button()` is called.
        self.reload_button = ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.REFRESH, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(
                        "Reload Library", size=12, color=ft.Colors.ON_SURFACE_VARIANT
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=5,
                tight=True,
            ),
            visible=False,
        )

    def build(self):
        """Build and return the splash view"""
        return ft.View(
            route="/splash",
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Text(
                                "SFSIS",
                                size=32,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE,
                            ),
                            ft.Text(
                                "Mobile Companion",
                                size=13,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Container(height=20),
                            self.progress_bar,
                            self.status_text,
                            self.reload_button,
                        ],
                    ),
                )
            ],
        )

    def set_progress(self, value: float | None, status: str | None = None):
        """Update progress bar value (0..1, or None for indeterminate) and status text"""
        self.progress_bar.value = value
        if status is not None:
            self.status_text.value = status
        self.page.update()

    def show_reload_button(self, on_click):
        """Reveal the "Reload Library" button, wired to `on_click`"""
        self.reload_button.on_click = on_click
        self.reload_button.visible = True
        self.page.update()
