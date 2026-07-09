import flet as ft

from components.module.view import ModuleView
from components.form.form import Form
from utils.http_client import HttpClient


class ModulePage:
    """Issue stock against a header.

    `record_id` here is the *stock out header* id (route:
    /modules/stock_out/item_new/<header_id>), not an item id — issuing is
    create-only. No hidden "id" field is declared below, so Form.serialize()
    never tries to inject a record key; the header id is sent explicitly as
    `stock_out_header_id` in callback_submit instead.
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
                "name": "qty_out", "label": "Qty Out", "icon": ft.Icons.NUMBERS,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "input", "autofocus": True
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
            start_blank=True
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Issue Stock")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        form_data = self.form.serialize()
        form_data["stock_out_header_id"] = self.header_id

        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/submit_item", data=form_data)

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("Stock issued successfully")
        self.page.run_task(
            self.page.push_route, f"/modules/{self.module}/edit/{self.header_id}"
        )
