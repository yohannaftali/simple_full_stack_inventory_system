"""Item sub-table embedded in a stock out header's edit screen, built on the
shared `components/table/table.py` (paginated list/search, same lazy-loading
contract as every other list screen). See `stock_in/item_table.py`'s
docstring for why a sub-table needs `Table`'s `custom_param`/`edit_screen`
support rather than being reused unmodified.

Stock out items are create-only (see `services.inventory_service` on the
backend for why issuing can't be edited), so - unlike stock_in's item
table - no field here is marked `"key": True`, giving no row-click
navigation (same convention as `stock_browse`/`usage_report`, which also
have no edit screen to navigate to). Just an "Add Item" button.
"""

import flet as ft

from components.table.table import Table


class ItemTable:
    """Item sub-table for a stock out header, with an "Add Item" button."""

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
                "type": "label"
            },
            {
                "name": "material_name", "label": "Material",
                "type": "label"
            },
            {
                "name": "location_code", "label": "Location",
                "type": "label"
            },
            {
                "name": "qty_out", "label": "Qty Out",
                "type": "label", "format": "number"
            },
            {
                "name": "price", "label": "Price",
                "type": "label", "format": "number"
            },
            {
                "name": "total_value", "label": "Total Value",
                "type": "label", "format": "number"
            },
            {
                "name": "remarks", "label": "Remarks",
                "type": "label"
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
