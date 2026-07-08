import flet as ft

from components.list.list import List


class ListForm:

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
        self.title = field.get("title", None)
        self.subtitle = field.get("subtitle", None)
        self.leading = field.get("leading", None)
        self.trailing = field.get("trailing", None)
        self.list = List(
            page=self.page,
            parent=self.parent,
            name=self.name,
            fields=self.fields,
            is_inside_form=True,
            title=self.title,
            subtitle=self.subtitle,
            leading=self.leading,
            trailing=self.trailing,
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

        list_container = ft.Container(
            content=self.list.build(),
            expand=True
        )
        controls.append(list_container)
        return ft.Container(
            content=ft.Column(
                controls=controls
            ),
            expand=True,
            margin=ft.Margin.only(top=10),
        )

    def get_data(self) -> list | None:
        return self.list.data

    def set_data(self, data: list):
        self.list.data = data

    def rebuild(self):
        data = self.get_data()
        if not data:
            return
        element = self.list
        element.tiles.load(data, append=False)
        if element.body and element.body.list_view:
            element.body.list_view.controls = element.tiles.build()

    def process_buttons(self):
        for btn in self.header_button:
            self.list.toolbar.add_button(
                position=btn.get("position", "right"),
                callback=btn.get("callback"),
                tooltip=btn.get("tooltip", None),
                icon=btn.get("icon", None),
                icon_color=btn.get("icon_color", None),
            )
