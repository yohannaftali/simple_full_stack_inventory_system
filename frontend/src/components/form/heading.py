import flet as ft


class HeadingForm:

    def __init__(self, field: dict):
        self.label = field.get("label")
        self.icon = field.get("icon")
        self.label_size = field.get("label_size", 16)
        self.label_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.bgcolor = field.get("bgcolor", ft.Colors.TRANSPARENT)
        self.weight = field.get("weight", ft.FontWeight.BOLD)
        self.max_lines = field.get("max_lines", 1)
        self.italic = field.get("italic", False)

    def build(self):
        controls = []
        icon = ft.Icon(
            icon=self.icon,
            color=self.label_color
        ) if self.icon is not None else None

        if icon is not None:
            controls.append(icon)

        text = ft.Text(
            value=self.label,
            size=self.label_size,
            color=self.label_color,
            bgcolor=self.bgcolor,
            weight=self.weight,
            selectable=False,
            max_lines=self.max_lines,
            italic=self.italic,
        ) if self.label is not None else None
        if text is not None:
            controls.append(text)

        return ft.Container(
            content=ft.Row(
                controls=controls
            ),
            expand=True,
            margin=ft.Margin.only(top=10),
        )
