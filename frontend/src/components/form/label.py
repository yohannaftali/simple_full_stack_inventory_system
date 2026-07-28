import flet as ft


class LabelForm:

    def __init__(self, field: dict):
        self.label = field.get("label", "")
        self.icon = field.get("icon")

        self.value_size = field.get("value_size", 14)
        self.label_size = field.get("label_size", 13)
        # M3 filled text field color roles - see components/form/input.py's
        # class docstring for the full spec-correction rationale (issue #53
        # follow-up). Fill/text are constant; only the label turns PRIMARY
        # on focus (a read-only label can still be tabbed to/focused).
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("label_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_label_color = field.get("focused_label_color", ft.Colors.PRIMARY)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_border_color = field.get("focused_border_color", ft.Colors.PRIMARY)
        self.multiline = field.get("multiline", False)
        self.min_lines = field.get("min_lines", 1)
        self.max_lines = field.get("max_lines", 1)
        self.prefix_icon = None
        self.filled = field.get("filled", True)
        self.bgcolor = field.get("bgcolor", ft.Colors.SURFACE_CONTAINER_HIGHEST)
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
            border_radius=10,
            border=ft.InputBorder.UNDERLINE,
            border_color=self.border_color,
            focused_border_color=self.focused_border_color,
            autofocus=False,
            text_size=self.value_size,
            read_only=True,
            color=self.value_color,
            content_padding=ft.Padding.only(
                left=12 if self.icon else 16, right=16, top=8, bottom=8
            ),
            label_style=ft.TextStyle(
                size=self.label_size,
                color=self.label_color,
            ),
            multiline=self.multiline,
            min_lines=self.min_lines,
            max_lines=self.max_lines,
            filled=self.filled,
            bgcolor=self.bgcolor,
            adaptive=True,
            expand=True,
            on_focus=self._on_focus,
            on_blur=self._on_blur,
        )
        return self.field

    def _on_focus(self, e=None) -> None:
        self.field.label_style = ft.TextStyle(size=self.label_size, color=self.focused_label_color)
        self._safe_update()

    def _on_blur(self, e=None) -> None:
        self.field.label_style = ft.TextStyle(size=self.label_size, color=self.label_color)
        self._safe_update()

    def _safe_update(self) -> None:
        try:
            self.field.update()
        except RuntimeError:
            pass
