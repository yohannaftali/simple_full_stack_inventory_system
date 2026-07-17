"""Item sub-table embedded in a stock movement header's edit screen, built on
the shared `components/table/table.py` (paginated list/search, same
lazy-loading contract as every other list screen). See
`stock_out/item_table.py`'s docstring for the underlying pattern.

Stock movement items are create-only (see `services.inventory_service` on
the backend), so no field here is marked `"key": True` - no row-click
navigation, same convention as `stock_out`'s own item table. Just an "Add
Item" button.
"""

import flet as ft

from components.table.table import Table


class ItemTable:
    """Item sub-table for a stock movement header, with an "Add Item" button."""

    def __init__(self, page: ft.Page, parent, module: str, header_id: str | int):
        self.page = page
        self.parent = parent  # the header's edit ModulePage
        self.module = module
        self.screen = f"{parent.screen}_items"
        self.header_id = header_id

        self.fields = [
            {
                "name": "id",
                "type": "hidden", "serialize": False
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
                "name": "origin_location_code", "label": "Origin Location Code",
                "type": "label", "sort": True
            },
            {
                "name": "origin_location_name", "label": "Origin Location",
                "type": "label", "sort": True
            },
            {
                "name": "destination_location_code", "label": "Destination Location Code",
                "type": "label", "sort": True
            },
            {
                "name": "destination_location_name", "label": "Destination Location",
                "type": "label", "sort": True
            },
            {
                "name": "plan_qty", "label": "Qty Plan",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "movement_qty", "label": "Qty Movement",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "remaining", "label": "Remaining",
                "type": "label", "format": "number"
            },
            {
                "name": "unit_name", "label": "Unit",
                "type": "label"
            },
            {
                "name": "remarks", "label": "Remarks",
                "type": "label", "sort": True
            },
            {
                "name": "created_at", "label": "Datetime Actual",
                "type": "label", "format": "datetime", "sort": True
            }
        ]

        self.table = Table(
            page=page,
            parent=self,
            name="items",
            fields=self.fields,
            endpoint=f"C_{module}/get_items",
            custom_param={"header_id": header_id},
        )

        self.table.toolbar.add_new_button(callback=self.callback_add_new)

    @property
    def view(self):
        """Delegate to the header edit page's view - Table.get_data() calls
        `self.parent.view.show_error(...)` on load failure."""
        return self.parent.view

    def build(self) -> ft.Control:
        return self.table.build()

    def callback_add_new(self, e):
        self.page.run_task(
            self.page.push_route, f"/modules/{self.module}/item_new/{self.header_id}"
        )
