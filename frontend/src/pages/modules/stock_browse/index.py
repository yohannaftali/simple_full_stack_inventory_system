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
                "type": "hidden", "key": True, "serialize": False
            },
            {
                "name": "material_code", "label": "Material Code",
                "type": "label", "sort": True
            },
            {
                "name": "material_name", "label": "Material",
                "type": "label", "sort": True
            },
            {
                "name": "location_code", "label": "Location Code",
                "type": "label", "sort": True
            },
            {
                "name": "location_name", "label": "Location",
                "type": "label", "sort": True
            },
            {
                "name": "qty", "label": "Qty",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "unit_name", "label": "Unit",
                "type": "label", "sort": True
            },
            {
                "name": "average_price", "label": "Avg Price",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "value", "label": "Value",
                "type": "label", "format": "number", "sort": True
            }
        ]

        self.view = ModuleView(page, module, screen)

        self.table = Table(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields,
            edit_screen="stock_by_material"
        )

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.table.build()
