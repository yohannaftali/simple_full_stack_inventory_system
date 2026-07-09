import flet as ft


class LabelForm:

    def __init__(self, field: dict):
        self.label = field.get("label", "")
        self.icon = field.get("icon")

        self.value_size = field.get("value_size", 16)
        self.label_size = field.get("label_size", 14)
        self.value_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.label_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.border_color = field.get("border_color", ft.Colors.TRANSPARENT)
        self.multiline = field.get("multiline", False)
        self.min_lines = field.get("min_lines", 1)
        self.max_lines = field.get("max_lines", 1)
        self.prefix_icon = None
        self.filled = field.get("filled", False)
        self.bgcolor = field.get("bgcolor", ft.Colors.TRANSPARENT)

    def build(self):
        self.prefix_icon = (
            ft.Icon(
                icon=self.icon,
                color=self.value_color) if self.icon is not None else None
        )
        return ft.TextField(
            label=self.label,
            hint_text="",
            prefix_icon=self.prefix_icon,
            border_radius=10,
            border_color=self.border_color,
            autofocus=False,
            text_size=self.value_size,
            read_only=True,
            color=self.value_color,
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
        )
