import flet as ft

from components.module.view import ModuleView
from components.table.table import Table


class ModulePage:
    """Read-only material usage/cost by department report."""

    def __init__(self, page: ft.Page, module: str, screen=str):
        self.page = page
        self.module = module
        self.screen = screen

        self.fields = [
            {
                "name": "department_id",
                "type": "hidden", "serialize": False
            },
            {
                "name": "department_code", "label": "Dept Code",
                "type": "label"
            },
            {
                "name": "department_name", "label": "Department",
                "type": "label"
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
                "name": "total_qty_out", "label": "Total Qty",
                "type": "label", "format": "number"
            },
            {
                "name": "total_cost", "label": "Total Cost",
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
