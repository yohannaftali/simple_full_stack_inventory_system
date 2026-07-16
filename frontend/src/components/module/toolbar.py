"""
Toolbar component for module
"""

import flet as ft

from components.button import Button


class ModuleToolbar:
    """Toolbar component compliant with Material 3 sub-header standards"""

    def __init__(self, page: ft.Page, left=None, right=None):
        """
        Initialize toolbar

        Args:
            page: The Flet page
        """
        self.page = page
        self.left = left if left is not None else []
        self.right = right if right is not None else []

    def build(self):
        """Build and return the toolbar component (Locked to precise 48dp height)"""
        if not self.left and not self.right:
            return ft.Container()

        return ft.Container(
            height=48,
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(controls=self.left, spacing=8)
                    if self.left
                    else ft.Container(),
                    ft.Row(controls=self.right, spacing=8)
                    if self.right
                    else ft.Container(),
                ],
            ),
        )

    def add_button(
        self,
        position,
        callback,
        icon=ft.Icons.ABC,
        tooltip="",
        bgcolor=None,
        icon_color=None,
    ):
        """Return a standard Material 3 icon button (32dp, transparent
        background - only the icon shows, with Flutter's own hover/pressed
        state-layer highlight). Pass `bgcolor` for the rare filled/tonal
        variant (e.g. a red "danger" delete button)."""
        btn_fg = (
            icon_color if icon_color is not None else ft.Colors.ON_SURFACE_VARIANT
        )

        button = Button(
            icon=icon,
            on_click=callback,
            tooltip=tooltip,
            icon_color=btn_fg,
            bgcolor=bgcolor,
            size=32,
            radius=16,
        ).build()
        if position == "right":
            self.right.append(button)
            return

        self.left.append(button)
        return

    def add_new_button(
        self,
        callback,
        icon=ft.Icons.ADD,
        tooltip="Add New",
        bgcolor=None,
        icon_color=None,
    ):
        """Return an 'Add New' button re-using add_button functional logic"""
        self.add_button(
            position="left",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            bgcolor=bgcolor,
            icon_color=icon_color,
        )

    def add_submit_button(
        self,
        callback,
        icon=ft.Icons.CHECK,
        tooltip="Submit",
        bgcolor=None,
        icon_color=None,
    ):
        """Return an 'Add Submit' button re-using add_button functional logic"""
        self.add_button(
            position="right",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            bgcolor=bgcolor,
            icon_color=icon_color,
        )
