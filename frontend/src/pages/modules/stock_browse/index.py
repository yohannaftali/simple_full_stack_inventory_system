import flet as ft

from components.module.view import ModuleView
from components.module.view_toggle import ViewToggle


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
                "name": "location_id",
                "type": "hidden", "serialize": False
            },
            {
                "name": "material_code", "label": "Material Code",
                "type": "label", "sort": True,
                "link_key_field": "material_id", "link_screen": "stock_by_material",
                # Explicit positions (issue #81) - this module has two
                # independent drill-down targets (material/location) that
                # both need to stay visible in the List view's primary
                # leading/title/subtitle slots, so they can't be left to
                # simple field-order auto-positioning (which would only
                # keep 3 of these 4 linked fields up front and bury the
                # 4th in the collapsed "extra" section, unreachable
                # without an extra tap).
                "position": "leading", "row": 0,
            },
            {
                "name": "material_name", "label": "Material",
                "type": "label", "sort": True,
                "link_key_field": "material_id", "link_screen": "stock_by_material",
                "position": "title", "row": 0,
            },
            {
                "name": "location_code", "label": "Location Code",
                "type": "label", "sort": True,
                "link_key_field": "location_id", "link_screen": "stock_by_location",
                "position": "subtitle", "row": 0,
            },
            {
                "name": "location_name", "label": "Location",
                "type": "label", "sort": True,
                "link_key_field": "location_id", "link_screen": "stock_by_location",
                "position": "subtitle", "row": 1,
            },
            {
                "name": "qty", "label": "Qty",
                "type": "label", "format": "number", "sort": True,
                "position": "extra",
            },
            {
                "name": "unit_name", "label": "Unit",
                "type": "label", "sort": True,
                "position": "extra",
            },
            {
                "name": "average_price", "label": "Avg Price",
                "type": "label", "format": "number", "sort": True,
                "position": "extra",
            },
            {
                "name": "value", "label": "Value",
                "type": "label", "format": "number", "sort": True,
                "position": "extra",
            }
        ]

        self.view = ModuleView(page, module, screen)

        self.toggle = ViewToggle(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields,
        )

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.toggle.build()
