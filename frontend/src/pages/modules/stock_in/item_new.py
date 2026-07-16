import flet as ft

from components.module.view import ModuleView
from components.form.form import Form
from utils.http_client import HttpClient


class ModulePage:
    """Add a receiving item to a header.

    `record_id` here is the *receiving header* id (route:
    /modules/stock_in/item_new/<header_id>), not an item id — this screen
    only ever creates. No hidden "id" field is declared below, so
    Form.serialize() never tries to inject a record key; the header id is
    sent explicitly as `receiving_header_id` in callback_submit instead.

    Also opts into the bulk-upload hamburger menu (issue #24) via
    `Form(bulk_input=True, ...)` — unlike the plain `Form(bulk_input=True)`
    every other module `new` screen uses, this one overrides `bulk_endpoint`
    (posts to `submit_bulk_item`, not the default `submit_bulk`),
    `bulk_extra_fields` (carries this screen's own `receiving_header_id` on
    every uploaded row, the same value `callback_submit` already sends for
    a single-item submit), and `bulk_redirect` (back to the header's edit
    screen, not `/modules/{module}/index` — there is no bare "index" for an
    item, only its owning header).
    """

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.header_id = record_id
        self.record_id = None

        self.fields = [
            {
                "name": "material_id", "label": "Material", "icon": ft.Icons.INVENTORY_2,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": "location_id", "label": "Location", "icon": ft.Icons.PLACE,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "select"
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
            name="new",
            fields=self.fields,
            start_blank=True,
            bulk_input=True,
            bulk_endpoint=f"C_{module}/submit_bulk_item",
            bulk_extra_fields={"receiving_header_id": str(self.header_id)},
            bulk_redirect=f"/modules/{module}/edit/{self.header_id}",
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Add Item")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        form_data = self.form.serialize()
        form_data["id"] = ""
        form_data["receiving_header_id"] = self.header_id

        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/submit_item", data=form_data)

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("Item added successfully")
        self.page.run_task(
            self.page.push_route, f"/modules/{self.module}/edit/{self.header_id}"
        )
