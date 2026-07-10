import flet as ft


class InputForm:

    def __init__(self, field: dict):
        self.label = field.get("label", "")
        self.hint_text = field.get("hint_text", f"Please input {self.label}")
        self.icon = field.get("icon")
        self.autofocus = field.get("autofocus", False)
        self.read_only = field.get("read_only", False)
        self.value_size = field.get("value_size", 16)
        self.label_size = field.get("label_size", 14)
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE)
        self.multiline = field.get("multiline", False)
        self.min_lines = field.get("min_lines", 1)
        self.max_lines = field.get("max_lines", 1)
        self.prefix_icon = None
        self.filled = field.get("filled", False)
        self.bgcolor = field.get("bgcolor", ft.Colors.TRANSPARENT)
        self.password = field.get("password", False)
        self.can_reveal_password = field.get("can_reveal_password", self.password)

    def build(self):
        self.prefix_icon = (
            ft.Icon(
                icon=self.icon,
                color=self.value_color) if self.icon is not None else None
        )
        return ft.TextField(
            label=self.label,
            hint_text=self.hint_text,
            prefix_icon=self.prefix_icon,
            border_radius=10,
            border_color=self.border_color,
            autofocus=self.autofocus,
            text_size=self.value_size,
            read_only=self.read_only,
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
            password=self.password,
            can_reveal_password=self.can_reveal_password,
            adaptive=True,
            expand=True,
        )
