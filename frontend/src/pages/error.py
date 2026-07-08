

import flet as ft

from components.module.header import ModuleHeader
from components.module.error_screen import ErrorScreen


class ErrorPage:
    """Error page class"""

    def __init__(self, page: ft.Page, target: str, module: str, screen: str, error: str):
        """
        Initialize Error Page

        Args:
            page: The Flet page
            target: string
            module: string
            screen: string
            error: string
        """
        self.page = page
        self.target = target
        self.module = module
        self.screen = screen
        self.error = error if error is not None else "Page not found"
        self.header = ModuleHeader(page)
        print(f"not found /{target}/{module}/{screen}.py")
        path = f"pages.{target}.{module}.{screen}"
        self.body = ErrorScreen(path, self.error)

    def build(self):
        """Build and return the home page UI"""
        return ft.View(
            route=f"/{self.target}/{self.module}/{self.screen}",
            controls=[
                self.header.build(),
                self.body.build(),
            ],
            spacing=0,
            padding=0,
            bgcolor=ft.Colors.SURFACE,
        )
