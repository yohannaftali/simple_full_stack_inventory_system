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
            parent: The calling module parent class reference
            left: Controls pushed to the absolute left boundary
            right: Controls pushed to the absolute right boundary
            controls: List of middleware controls (e.g., Search Bar field)
        """
        self.page = page
        self.parent = parent
        self.left = left if left is not None else []
        self.right = right if right is not None else []
        self.controls = controls if controls is not None else []

    def build(self):
        """Build and return the toolbar component"""
        right_controls = list(self.right) if self.right else []
        if hasattr(self.parent, "export_menu") and self.parent.export_menu:
            right_controls.append(self.parent.export_menu.build())

        if not self.left and not right_controls and not self.controls:
            return ft.Container()

        return ft.Container(
            height=48,  # Forces layout boundary limits to match precise M3 standards
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # Left-aligned controls
                    ft.Row(controls=self.left, spacing=8)
                    if self.left
                    else ft.Container(),
                    # Middle-expanded custom layout track (Houses your compact search bar)
                    ft.Row(
                        controls=self.controls,
                        expand=True,
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    # Right-aligned actions
                    ft.Row(controls=right_controls, spacing=8)
                    if right_controls
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
        """Return an button"""
        # Maintain design continuity utilizing your custom standard token mappings
        btn_bg = bgcolor if bgcolor is not None else ft.Colors.ON_SURFACE
        btn_fg = (
            icon_color if icon_color is not None else ft.Colors.SURFACE_CONTAINER_HIGH
        )

        button = ft.IconButton(
            icon=icon,
            icon_color=btn_fg,
            tooltip=tooltip,
            on_click=callback,
            height=32,
            width=32,
            style=ft.ButtonStyle(
                bgcolor=btn_bg,
                padding=0,  # Forces graphic straight to geometric center
                shape=ft.RoundedRectangleBorder(radius=16),
            ),
        )
        if position == "right":
            self.right.append(button)
            return
        if position == "left":
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
        """Add a compact new button to the toolbar"""
        self.add_button(
            position="right",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            bgcolor=bgcolor,
            icon_color=icon_color,
        )

    def add_save_button(
        self,
        callback,
        icon=ft.Icons.SAVE,
        tooltip="Save",
        bgcolor=None,
        icon_color=None,
    ):
        """Return an 'Add Save' button"""
        self.add_button(
            position="right",
            callback=callback,
            icon=icon,
            tooltip=tooltip,
            bgcolor=bgcolor,
            icon_color=icon_color,
        )
