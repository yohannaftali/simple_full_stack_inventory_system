"""
Shared Button component (Material 3 standard), reused across toolbars and screens
"""

import flet as ft


class Button:
    """
    Material 3 standard button.

    Renders a plain, Flet-default `IconButton` when `size` is left as `None`
    (matches a bare toolbar icon button), or a compact, pill-shaped
    `IconButton` when `size` is set (matches the 32dp toolbar buttons already
    in use). Passing `label` renders a `FilledButton` (icon + text) instead
    of an icon-only button.
    """

    def __init__(
        self,
        icon,
        on_click,
        tooltip="",
        label=None,
        icon_color=None,
        bgcolor=None,
        size=None,
        radius=None,
        padding=0,
    ):
        self.icon = icon
        self.on_click = on_click
        self.tooltip = tooltip
        self.label = label
        self.icon_color = icon_color
        self.bgcolor = bgcolor
        self.size = size
        self.radius = radius if radius is not None else (size / 2 if size else None)
        self.padding = padding

    def build(self):
        if self.label:
            return ft.FilledButton(
                text=self.label,
                icon=self.icon,
                icon_color=self.icon_color,
                tooltip=self.tooltip,
                on_click=self.on_click,
                bgcolor=self.bgcolor,
                height=self.size,
            )

        if self.size is None:
            return ft.IconButton(
                icon=self.icon,
                icon_color=self.icon_color,
                tooltip=self.tooltip,
                on_click=self.on_click,
            )

        return ft.IconButton(
            icon=self.icon,
            icon_color=self.icon_color,
            tooltip=self.tooltip,
            on_click=self.on_click,
            height=self.size,
            width=self.size,
            style=ft.ButtonStyle(
                bgcolor=self.bgcolor,
                padding=self.padding,
                shape=ft.RoundedRectangleBorder(radius=self.radius),
            ),
        )
