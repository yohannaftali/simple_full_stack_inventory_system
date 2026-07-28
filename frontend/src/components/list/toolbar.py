"""
Toolbar component for table
"""

import flet as ft

from components.button import Button


class ListToolbar:
    """Toolbar component"""

    def __init__(self, page: ft.Page, parent, left=None, right=None, controls: list = None):
        """
        Initialize toolbar

        Args:
            page: The Flet page
        """
        self.page = page
        self.parent = parent
        self.controls = controls if controls is not None else []
        self.left = left
        self.right = right

    def build(self):
        """Build and return the toolbar component"""
        if self.left is None and self.right is None and not self.controls:
            return ft.Container()
        
        # Filter out None values from controls
        safe_controls = [c for c in self.controls if c is not None]
        safe_left = [c for c in self.left if c is not None] if self.left else None
        safe_right = [c for c in self.right if c is not None] if self.right else None

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Row(
                            controls=safe_left)) if safe_left else ft.Container(),
                    ft.Row(
                        controls=safe_controls,
                        expand=True,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    ft.Container(
                        content=ft.Row(
                            controls=safe_right)) if safe_right else ft.Container(),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.all(10),
            bgcolor=ft.Colors.PRIMARY,
        )

    def add_button(self, position, callback, icon=ft.Icons.ABC, tooltip="", icon_color=None):
        """Return an button"""
        button = Button(
            icon=icon,
            on_click=callback,
            tooltip=tooltip,
            icon_color=icon_color or ft.Colors.ON_PRIMARY,
        ).build()
        if position == "right":
            self.right = [] if self.right is None else self.right
            self.right.append(
                button
            )
            return
        if position == "left":
            self.left = [] if self.left is None else self.left
            self.left.append(
                button
            )
            return

    def add_new_button(self, callback, icon=ft.Icons.ADD, tooltip="Add New", icon_color=None):
        """Add a new button to the toolbar"""
        self.add_button(
            position="right",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            icon_color=icon_color
        )

    def add_save_button(self, callback, icon=ft.Icons.SAVE, tooltip="Save", icon_color=None):
        """Return an 'Add Save' button"""
        self.add_button(
            position="right",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            icon_color=icon_color
        )

    def add_filter_button(self, callback, icon=ft.Icons.FILTER_LIST, tooltip="Toggle Filters", icon_color=None):
        """Add the per-field search/sort panel toggle button (issue #55),
        same shape as TableToolbar.add_filter_button (issue #10/#20)."""
        self.add_button(
            position="left",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            icon_color=icon_color
        )
