import flet as ft

from components.module.view import ModuleView
from components.table.table import Table


class ModulePage:
    """Read-only current-stock listing."""

    def __init__(self, page: ft.Page, module: str, screen=str):
        self.page = page
        self.module = module
        self.screen = screen

        self.fields = [
            {
                "name": "material_id",
                "type": "hidden", "serialize": False
            },
            {
                "name": "material_code", "label": "Material Code",
                "type": "label"
            },
            {
                "name": "material_name", "label": "Material",
                "type": "label"
            },
            {
                "name": "location_code", "label": "Location Code",
                "type": "label"
            },
            {
                "name": "location_name", "label": "Location",
                "type": "label"
            },
            {
                "name": "qty", "label": "Qty",
                "type": "label", "format": "number"
            },
            {
                "name": "average_price", "label": "Avg Price",
                "type": "label", "format": "number"
            },
            {
                "name": "value", "label": "Value",
                "type": "label", "format": "number"
            }
        ]

        self.view = ModuleView(page, module, screen)

        self.table = Table(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields
        )

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.table.build()
