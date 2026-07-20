"""Item sub-table embedded in a receiving header's edit screen, built on the
shared `components/table/table.py` (paginated list/search, same lazy-loading
contract as every other list screen: `table-keyword-filter`/`limit`/`page`/
`offset`, with `db_total_page`/`db_num_rows` on the first row).

Not simply reused as-is: `Table`'s row click always builds
`/modules/{module}/edit/{id}`, which would collide with this same module's
header edit screen. `Table.edit_screen` (and `custom_param` to scope every
request to this one header) exist specifically so this sub-table can reuse
the shared component instead of a bespoke widget - row clicks go to
`item_edit/<item_id>` here instead.
"""

import flet as ft

from components.table.table import Table


class ItemTable:
    """Item sub-table for a receiving header, with an "Add Item" button."""

    def __init__(self, page: ft.Page, parent, module: str, header_id: str | int):
        self.page = page
        self.parent = parent  # the header's edit ModulePage
        self.module = module
        self.screen = f"{parent.screen}_items"
        self.header_id = header_id

        self.fields = [
            {
                "name": "id",
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
                "name": "location_code", "label": "Location",
                "type": "label", "sort": True
            },
            {
                "name": "qty_plan", "label": "Qty Plan",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "qty_received", "label": "Qty",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "unit_name", "label": "Unit",
                "type": "label", "sort": True
            },
            {
                "name": "price_buy", "label": "Price",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "remarks", "label": "Remarks",
                "type": "label", "sort": True
            }
        ]

        self.table = Table(
            page=page,
            parent=self,
            name="items",
            fields=self.fields,
            endpoint=f"C_{module}/get_items",
            custom_param={"header_id": header_id},
            edit_screen="item_edit",
            fill_available_space=False,
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
