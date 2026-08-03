import flet as ft

from components.form.input import (
    FIELD_BORDER_RADIUS,
    HELPER_TEXT_STYLE,
    field_content_padding,
)


class LabelForm:

    def __init__(self, field: dict):
        self.label = field.get("label", "")
        self.icon = field.get("icon")

        self.value_size = field.get("value_size", 14)
        self.label_size = field.get("label_size", 13)
        # M3 outlined colour roles - see components/form/input.py's class
        # docstring (issue #79). No container fill; focused-state colouring
        # is left to Flutter/M3 rather than swapped from Python.
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("label_color", ft.Colors.ON_SURFACE_VARIANT)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_border_color = field.get("focused_border_color", ft.Colors.PRIMARY)
        self.multiline = field.get("multiline", False)
        self.min_lines = field.get("min_lines", 1)
        self.max_lines = field.get("max_lines", 1)
        self.prefix_icon = None
        self.filled = field.get("filled", False)
        self.bgcolor = field.get("bgcolor")
        # Always present, even blank (issue #78) - see input.py's own
        # HELPER_TEXT_STYLE notes for why every field reserves this
        # space unconditionally.
        self.helper_text = field.get("helper_text", "")
        self.field: ft.TextField | None = None

    def build(self):
        self.prefix_icon = (
            ft.Icon(
                icon=self.icon,
                color=ft.Colors.ON_SURFACE_VARIANT) if self.icon is not None else None
        )
        self.field = ft.TextField(
            label=self.label,
            hint_text="",
            prefix_icon=self.prefix_icon,
            # No explicit `height` (issue #79) - every field type shares the
            # same border, content padding, text size and an always-present
            # helper line, so they all size to the same height naturally.
            helper=self.helper_text,
            helper_style=HELPER_TEXT_STYLE,
            border_radius=FIELD_BORDER_RADIUS,
            border=ft.InputBorder.OUTLINE,
            border_color=self.border_color,
            focused_border_color=self.focused_border_color,
            autofocus=False,
            text_size=self.value_size,
            read_only=True,
            color=self.value_color,
            content_padding=field_content_padding(self.icon is not None),
            label_style=ft.TextStyle(
                size=self.label_size,
                color=self.label_color,
            ),
            multiline=self.multiline,
            min_lines=self.min_lines,
            max_lines=self.max_lines,
            filled=self.filled,
            bgcolor=self.bgcolor,
            # No `adaptive=True` (issue #73) - see main.py's `page.adaptive`
            # removal note.
            expand=True,
        )
        return self.field
