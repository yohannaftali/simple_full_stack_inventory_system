"""
Toolbar component for table
"""

import flet as ft


class TableToolbar:
    """Toolbar component"""

    def __init__(
        self, page: ft.Page, parent, left=None, right=None, controls: list = None
    ):
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

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(content=ft.Row(controls=self.left))
                    if self.left
                    else ft.Container(),
                    ft.Row(
                        controls=self.controls,
                        expand=True,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    ft.Container(content=ft.Row(controls=self.right))
                    if self.right
                    else ft.Container(),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.all(10),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )

    def add_button(
        self,
        position,
        callback,
        icon=ft.Icons.ABC,
        tooltip="",
        icon_color=ft.Colors.ON_PRIMARY_CONTAINER,
    ):
        """Return an button"""
        button = ft.IconButton(
            icon=icon,
            icon_color=icon_color,
            tooltip=tooltip,
            on_click=callback,
        )
        if position == "right":
            self.right = [] if self.right is None else self.right
            self.right.append(button)
            return
        if position == "left":
            self.left = [] if self.left is None else self.left
            self.left.append(button)
            return

    def add_new_button(
        self,
        callback,
        icon=ft.Icons.ADD,
        tooltip="Add New",
        icon_color=ft.Colors.ON_PRIMARY_CONTAINER,
    ):
        """Add a new button to the toolbar"""
        self.add_button(
            position="right",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            icon_color=icon_color,
        )

    def add_save_button(
        self,
        callback,
        icon=ft.Icons.SAVE,
        tooltip="Save",
        icon_color=ft.Colors.ON_PRIMARY_CONTAINER,
    ):
        """Return an 'Add Save' button"""
        self.add_button(
            position="right",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            icon_color=icon_color,
        )
