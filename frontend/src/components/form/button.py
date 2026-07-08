import flet as ft


class ButtonForm:

    def __init__(self, field: dict):
        self.label = field.get("label", "")
        self.tooltip = field.get("tooltip")
        self.icon = field.get("icon")
        self.label_size = field.get("label_size", 16)
        self.label_color = field.get("color", ft.Colors.ON_PRIMARY_CONTAINER)
        self.bgcolor = field.get("bgcolor", ft.Colors.PRIMARY)
        self.on_click = field.get("on_click", None)
        self.disabled = field.get("disabled", False)
        self.alignment = field.get("alignment", ft.Alignment.CENTER)
        self.width = field.get("width")
        self.height = field.get("height", 50)

    def build(self):
        return ft.Container(
            content=ft.TextButton(
                content=self.label,
                tooltip=self.tooltip,
                icon=self.icon,
                icon_color=self.label_color,
                on_click=self.on_click,
                disabled=self.disabled,
                height=self.height,
                width=self.width,
                expand=True,
                style=ft.ButtonStyle(
                    color=self.label_color,
                    bgcolor=self.bgcolor,
                    shape=ft.RoundedRectangleBorder(radius=10),
                )
            ),
            alignment=self.alignment,
            expand=True
        )
