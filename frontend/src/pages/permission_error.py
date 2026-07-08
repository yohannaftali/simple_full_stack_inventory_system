

import flet as ft

from components.module.header import ModuleHeader
from components.module.permission_error_screen import PermissionErrorScreen


class PermissionErrorPage:
    """Permission Error page class"""

    def __init__(self, page: ft.Page, module: str, screen=str):
        """
        Initialize Permission Error Page

        Args:
            page: The Flet page
            module: string
            screen: string
        """
        self.page = page
        self.module = module
        self.screen = screen

        self.header = ModuleHeader(page)
        print("Permission denied")
        self.body = PermissionErrorScreen(module, 'Permission denied')

    def build(self):
        """Build and return the home page UI"""
        return ft.View(
            route=f"/modules/{self.module}/{self.screen}",
            controls=[
                self.header.build(),
                self.body.build(),
            ],
            spacing=0,
            padding=0,
            bgcolor=ft.Colors.SURFACE,
        )
