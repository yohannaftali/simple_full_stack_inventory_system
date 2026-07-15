import flet as ft

from components.module.view import ModuleView
from components.table.table import Table


class ModulePage:
    """Module page class"""

    def __init__(self, page: ft.Page, module: str, screen=str):
        self.page = page
        self.module = module
        self.screen = screen

        self.fields = [
            {
                "name": "id",
                "type": "hidden", "key": True, "serialize": False
            },
            {
                "name": "date", "label": "Date",
                "type": "label", "format": "date"
            },
            {
                "name": "description", "label": "Description",
                "type": "label"
            },
            {
                "name": "supplier_name", "label": "Supplier",
                "type": "label"
            }
        ]

        self.view = ModuleView(page, module, screen)

        self.table = Table(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields
        )

        self.table.toolbar.add_new_button(callback=self.callback_add_new)

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.table.build()

    def callback_add_new(self, e):
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/new")
