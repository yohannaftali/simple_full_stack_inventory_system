import flet as ft

from components.table.table import Table


class TableForm:

    def __init__(self, page, parent, field: dict):
        self.page = page
        self.parent = parent
        self.name = field.get("name", "")
        self.label = field.get("label", "")
        self.label_size = field.get("label_size", 16)
        self.label_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.bgcolor = field.get("bgcolor", ft.Colors.TRANSPARENT)
        self.weight = field.get("weight", ft.FontWeight.BOLD)
        self.max_lines = field.get("max_lines", 1)
        self.italic = field.get("italic", False)
        self.icon = field.get("icon", "")

        self.fields: dict = field.get("content", {})
        self.header_button = field.get("header_button", [])
        self.table = Table(
            page=self.page,
            parent=self.parent,
            name=self.name,
            fields=self.fields,
        )
        self.process_buttons()

    def build(self):
        controls = []
        controls_title = []

        icon = ft.Icon(
            icon=self.icon,
            color=self.label_color
        ) if self.icon is not None else None

        if icon is not None:
            controls_title.append(icon)

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
            controls_title.append(text)

        title = ft.Container(
            content=ft.Row(
                controls=controls_title
            ),
        ) if len(controls_title) > 0 else None

        if title is not None:
            controls.append(title)

        table_container = ft.Container(
            content=self.table.build(),
            expand=True
        )
        controls.append(table_container)

        return ft.Container(
            content=ft.Column(
                controls=controls
            ),
            expand=True,
            margin=ft.Margin.only(top=10),
        )

    def rebuild(self):
        data = self.get_data()
        if not data:
            return

        element = self.table
        element.columns.load(data)
        element.rows.load(data, append=False)
        if element.table_container and element.header and element.body:
            controls_list = element.table_container.content.controls
            if isinstance(controls_list, list) and len(controls_list) >= 2:
                if element.toolbar:
                    controls_list[1] = element.header.build(
                    )
                    controls_list[2] = element.body.build()
                else:
                    controls_list[0] = element.header.build(
                    )
                    controls_list[1] = element.body.build()

    def get_data(self) -> list | None:
        return self.table.data

    def set_data(self, data: list):
        self.table.data = data

    def process_buttons(self):
        for btn in self.header_button:
            self.table.toolbar.add_button(
                position=btn.get("position", "right"),
                callback=btn.get("callback"),
                tooltip=btn.get("tooltip", None),
                icon=btn.get("icon", None),
                icon_color=btn.get("icon_color", None),
            )
