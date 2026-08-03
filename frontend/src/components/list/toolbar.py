"""
Toolbar component for table
"""

import flet as ft

from components.button import TOUCH_TARGET_RADIUS, TOUCH_TARGET_SIZE, Button
from components.table.toolbar import TOOLBAR_HEIGHT


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
        # Same hook as TableToolbar.build() - a List with an export_menu
        # (issue #56, suppressed for is_inside_form lists) gets the download
        # hamburger for free at the far right, no per-screen wiring needed.
        right = list(self.right) if self.right else []
        if hasattr(self.parent, "export_menu") and self.parent.export_menu:
            right.append(self.parent.export_menu.build())

        if self.left is None and not right and not self.controls:
            return ft.Container()

        # Filter out None values from controls
        safe_controls = [c for c in self.controls if c is not None]
        safe_left = [c for c in self.left if c is not None] if self.left else None
        safe_right = [c for c in right if c is not None] if right else None

        # Styling matches TableToolbar.build() exactly (issue #62) - a
        # List screen's toolbar used to render a solid filled PRIMARY bar
        # with no fixed height (pre-#21 design), visibly different from
        # every Table-based screen's low-emphasis SURFACE_CONTAINER_LOW bar
        # with a bottom hairline - most noticeable since issue #56 put a
        # Table/List view toggle on the same screen, where switching views
        # used to also visibly change the toolbar's color/height.
        return ft.Container(
            height=TOOLBAR_HEIGHT,
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
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
        )

    def add_button(self, position, callback, icon=ft.Icons.ABC, tooltip="", icon_color=None):
        """Return an button - standard M3 icon button (issue #62), matching
        TableToolbar.add_button()'s default: transparent background, no
        forced bgcolor unless a caller passes one explicitly.

        Sized to `TOUCH_TARGET_SIZE`/`TOUCH_TARGET_RADIUS` (issue #76) -
        without an explicit size, `Button` falls back to a plain,
        Flet-default `IconButton` (an unconstrained ~48dp tap target) that
        doesn't actually fit centered within this toolbar's
        `TOOLBAR_HEIGHT`-tall/8px-vertical-padding content area the way
        `export_menu`'s already-matching hamburger does. Matches
        `TableToolbar.add_button()`'s own sizing exactly."""
        button = Button(
            icon=icon,
            on_click=callback,
            tooltip=tooltip,
            icon_color=icon_color or ft.Colors.ON_SURFACE_VARIANT,
            size=TOUCH_TARGET_SIZE,
            radius=TOUCH_TARGET_RADIUS,
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
