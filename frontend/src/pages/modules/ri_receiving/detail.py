import flet as ft

from components.module.view import ModuleView
from components.list.list import List


class ModulePage:
    """Module page class"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        """
        Initialize Module Page

        Args:
            page: The Flet page
            module: string
            screen: string
            record_id: string | int (inspection_header_id)
        """
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id  # This is the inspection_header_id

        self.fields = [
            {
                "name": "inspection_detail_id",
                "type": "hidden"
            },
            {
                "name": "vin_no",
                "position": "title"
            },
            {
                "name": "engine_no",
                "position": "subtitle", "row": 0
            },
            {
                "name": "model_code",
                "position": "leading", "row": 0
            },
            {
                "name": "color_name",
                "position": "leading", "row": 1
            },
        ]

        # Custom endpoint with inspection_header_id parameter
        endpoint = f"C_{module}/get_detail_items?inspection_header_id={record_id}" if record_id else f"C_{module}/get_detail_items"

        self.view = ModuleView(page, module, screen)

        self.list = List(
            page=page,
            parent=self,
            name="detail_items",
            fields=self.fields,
            endpoint=endpoint
        )

        self.list.toolbar.add_button(
            position="right",
            icon=ft.Icons.REFRESH,
            tooltip="Refresh",
            callback=self.callback_refresh
        )

    def build(self):
        """Build and return the module screen page UI"""
        view = self.view.build(self.body(), padding=0)
        view.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            tooltip="Add",
            on_click=lambda e:
            self.page.run_task(self.page.push_route, f"/modules/{self.module}/edit/{self.record_id}")
        )
        return view

    def body(self):
        return self.list.build()

    def on_sort(self, e):
        print(f"{e.column_index}, {e.ascending}")

    def callback_refresh(self, e):
        self.list.page_number = 1
        self.list.get_data()
        print("refresh")
