"""
Toolbar component for module
"""

import flet as ft


class ModuleToolbar:
    """Toolbar component"""

    def __init__(self, page: ft.Page, left=None, right=None):
        """
        Initialize toolbar

        Args:
            page: The Flet page
        """
        self.page = page
        self.left = left
        self.right = right

    def build(self):
        """Build and return the toolbar component"""
        if self.left is None and self.right is None:
            return ft.Container()

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Row(
                            controls=self.left)) if self.left else ft.Container(),
                    ft.Row(
                        controls=[],
                        expand=True,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    ft.Container(
                        content=ft.Row(
                            controls=self.right)) if self.right else ft.Container(),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.all(10),
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
        )

    def add_button(self, position, callback, icon=ft.Icons.ABC, tooltip="", bgcolor=ft.Colors.PRIMARY, icon_color=ft.Colors.ON_PRIMARY):
        """Return an button"""
        button = ft.IconButton(
            icon=icon,
            icon_color=icon_color,
            tooltip=tooltip,
            on_click=callback,
            style=ft.ButtonStyle(
                color=icon_color,
                bgcolor=bgcolor,
                shape=ft.RoundedRectangleBorder(radius=30),
            )
        )
        if position == "right":
            self.right = [] if self.right is None else self.right
            self.right.append(
                button
            )
            return
        self.left = [] if self.left is None else self.left
        self.left.append(
            button
        )
        return

    def add_new_button(self, callback, icon=ft.Icons.ADD, tooltip="Add New", bgcolor=ft.Colors.PRIMARY, icon_color=ft.Colors.ON_PRIMARY):
        """Return an 'Add New' button"""
        self.add_button(
            position="left",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            bgcolor=bgcolor,
            icon_color=icon_color
        )

    def add_submit_button(self, callback, icon=ft.Icons.CHECK, tooltip="Submit", bgcolor=ft.Colors.PRIMARY, icon_color=ft.Colors.ON_PRIMARY):
        """Return an 'Add Submit' button"""
        self.add_button(
            position="right",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            bgcolor=bgcolor,
            icon_color=icon_color
        )
