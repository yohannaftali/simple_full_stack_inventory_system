import flet as ft

from components.module.view import ModuleView
from components.form.form import Form
from utils.http_client import HttpClient


class ModulePage:
    """Edit a receiving item's qty/price/remarks.

    Material and location are immutable once created (see
    services.inventory_service on the backend for why) — shown as read-only
    labels, not editable selects.
    """

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        # Fetch the header id up front (separate from Form's own GET below)
        # so callback_submit can navigate back to the right header afterward.
        client = HttpClient(self.page)
        item = client.get(f"C_{module}/get_item", {"id": record_id})
        self.header_id = item.get("receiving_header_id") if isinstance(item, dict) else None

        self.fields = [
            {
                "name": "id", "type": "hidden",
                "key": True,
            },
            {
                "name": "material_name", "label": "Material", "icon": ft.Icons.INVENTORY_2,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "label"
            },
            {
                "name": "location_name", "label": "Location", "icon": ft.Icons.PLACE,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "label"
            },
            {
                "name": "qty_received", "label": "Qty Received", "icon": ft.Icons.NUMBERS,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "input", "autofocus": True
            },
            {
                "name": "price_buy", "label": "Price", "icon": ft.Icons.ATTACH_MONEY,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "remarks", "label": "Remarks", "icon": ft.Icons.NOTES,
                "row": 3,
                "type": "input"
            }
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="edit",
            fields=self.fields
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Edit Item")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        form_data = self.form.serialize()

        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/submit_item", data=form_data)

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("Item updated successfully")
        self.page.run_task(
            self.page.push_route, f"/modules/{self.module}/edit/{self.header_id}"
        )
