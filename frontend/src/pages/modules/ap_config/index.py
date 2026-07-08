import flet as ft

from components.module.view import ModuleView
from components.table.table import Table


class ModulePage:
    """Module page class"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        """
        Initialize Module Page

        Args:
            page: The Flet page
            module: string
            screen: string
            record_id: string | int
        """
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        self.fields = [
            {
                "name": "id",
                "type": "hidden", "key": True, "serialize": False
            },
            {
                "name": "config_id", "label": "Id",
                "type": "label"
            },
            {
                "name": "config_key", "label": "Key",
                "type": "label"
            },
            {
                "name": "config_value", "label": "Value",
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
        """Build and return the module screen page UI"""
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.table.build()

    def on_sort(self, e):
        print(f"{e.column_index}, {e.ascending}")

    def callback_add_new(self, e):
        print("add new config")
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/new")
