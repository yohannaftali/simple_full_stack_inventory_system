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
            record_id: string | int
        """
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        self.fields = [
            {
                "name": "dn_number",
                "type": "hidden", "key": True
            },
            {
                "name": "out_date", "icon": ft.Icons.DATE_RANGE,
                "position": "leading", "row": 0
            },
            {
                "name": "status",
                "position": "leading", "row": 1
            },
            {
                "name": "dn_number",
                "position": "title"
            },
            {
                "name": "license_plate",
                "position": "subtitle", "row": 0
            },
            {
                "name": "driver_name",
                "position": "subtitle", "row": 0
            },
            {
                "name": "count_cbu", "icon": ft.Icons.DIRECTIONS_CAR,
                "position": "trailing", "row": 0
            },
            {
                "name": "inbound_time",
                "position": "trailing", "row": 1
            },
        ]

        self.view = ModuleView(page, module, screen)

        self.list = List(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields
        )

        self.list.toolbar.add_button(
            position="right",
            icon=ft.Icons.REFRESH,
            tooltip="Refresh",
            callback=self.callback_refresh
        )

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.list.build()

    def on_sort(self, e):
        print(f"{e.column_index}, {e.ascending}")

    def callback_refresh(self, e):
        endpoint = f"C_{self.module}/refresh_data"
        self.view.try_get(endpoint)
        print("refresh")
