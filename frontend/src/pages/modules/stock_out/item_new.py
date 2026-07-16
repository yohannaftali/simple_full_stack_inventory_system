import flet as ft

from components.form.menu import MenuForm
from components.module.view import ModuleView
from components.table.table import Table
from utils.http_client import HttpClient


class ModulePage:
    """Issue stock against a header.

    `record_id` here is the *stock out header* id (route:
    /modules/stock_out/item_new/<header_id>), not an item id — issuing is
    create-only.

    Unlike a plain Form screen, this one is hand-built: picking a material
    loads a shared `components/table/table.py` `Table` (same widget every
    other list screen uses) against C_stock_out/get_stock_by_material, one
    row per location currently holding stock of that material. The "Qty
    Issue"/"Remarks" columns are `"type": "input"` fields - `Table`/`Rows`
    render those as editable `ft.TextField`s instead of read-only text (see
    components/table/rows.py), and `Table.get_rows_with_input_values()`
    reads back what the user typed. Submitting posts one
    stock_out_header_id/material_id pair plus a repeated
    location_id/qty_out/remarks triplet per row with a qty > 0
    (C_stock_out/submit_items) — the backend creates one stock_out_item per
    location, each deducted FIFO within that location.

    Also gets a bulk-upload hamburger menu (issue #25), **independent of**
    the material dropdown above - the dropdown+table flow only ever issues
    one material per screen visit, but a bulk file can list several
    different materials in the same batch (Material | Location | Qty Issue
    | Remarks per row). Since this screen has no `Form` at all, it
    constructs `components/form/menu.py::MenuForm` directly (that component
    only ever needed `parent`/`fields`, not a real `Form` instance) instead
    of going through `Form(bulk_input=True)` like every other bulk-eligible
    screen - posts to `C_{module}/submit_bulk_items` (not the single-material
    `submit_items` the manual flow above uses) with `stock_out_header_id`
    riding along on every row, same convention as stock_in's `item_new`
    (issue #24).
    """

    def __init__(
        self, page: ft.Page, module: str, screen=str, record_id: str | int = None
    ):
        self.page = page
        self.module = module
        self.screen = screen
        self.header_id = record_id
        self.record_id = None

        self.material_options: list = []
        self.material_dropdown: ft.Dropdown | None = None
        self.stock_info_text = ft.Text("", size=12, visible=False)

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Issue Stock")
        self.view.toolbar.add_submit_button(callback=self.callback_submit)

        self.bulk_menu = MenuForm(
            page=page,
            parent=self,
            fields=[
                {"name": "material_id", "label": "Material", "type": "select"},
                {"name": "location_id", "label": "Location", "type": "select"},
                {"name": "qty_out", "label": "Qty Issue", "type": "input"},
                {"name": "remarks", "label": "Remarks", "type": "input"},
            ],
            endpoint=f"C_{module}/submit_bulk_items",
            extra_fields={"stock_out_header_id": str(self.header_id)},
            redirect_route=f"/modules/{module}/edit/{self.header_id}",
        )
        if self.view.toolbar.right is None:
            self.view.toolbar.right = []
        self.view.toolbar.right.append(self.bulk_menu.build())

        self.stock_table = Table(
            page=page,
            parent=self,
            name="stock_by_material",
            fields=[
                {"name": "location_code", "label": "Code"},
                {"name": "location_name", "label": "Location"},
                {"name": "qty", "label": "Qty Stock", "format": "number"},
                {"name": "unit_name", "label": "Unit"},
                {
                    "name": "qty_issue",
                    "label": "Qty Issue",
                    "type": "input",
                    "hint_text": "0",
                    "keyboard_type": ft.KeyboardType.NUMBER,
                },
                {
                    "name": "remarks",
                    "label": "Remarks",
                    "type": "input",
                    "hint_text": "Optional",
                },
            ],
            endpoint=f"C_{module}/get_stock_by_material",
            # Nothing to fetch until a material is picked - see
            # on_material_select() below.
            is_inside_form=True,
        )

        self._load_material_options()

    def build(self):
        return self.view.build(self.body())

    def body(self):
        self.material_dropdown = ft.Dropdown(
            label="Material",
            hint_text="Select a material",
            leading_icon=ft.Icon(ft.Icons.INVENTORY_2),
            border_radius=10,
            autofocus=True,
            options=[
                ft.DropdownOption(key=opt.get("value", ""), text=opt.get("label", ""))
                for opt in self.material_options
            ],
            expand=True,
            on_select=self.on_material_select,
        )

        return ft.Column(
            controls=[
                ft.Container(
                    content=self.material_dropdown,
                    padding=ft.Padding.symmetric(horizontal=20, vertical=10),
                ),
                ft.Container(
                    content=self.stock_info_text,
                    padding=ft.Padding.symmetric(horizontal=20),
                ),
                # Table's internal layout expands to fill its parent, which
                # needs a bounded height when nested alongside other content
                # in a scrolling Column - same fix as stock_out/edit.py's
                # item sub-table. No horizontal padding here (unlike the
                # controls above) - Columns.get_usable_width() sizes columns
                # off the raw page width with no way to know about padding
                # applied outside the table, so adding any here just starves
                # the last column of that many pixels and clips it.
                ft.Container(
                    content=self.stock_table.build(),
                    height=400,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _load_material_options(self):
        client = HttpClient(self.page)
        response = client.get(f"C_{self.module}/call_material_id_select")
        if isinstance(response, list):
            self.material_options = response

    def on_material_select(self, e):
        material_id = self.material_dropdown.value if self.material_dropdown else None
        self.stock_info_text.visible = False
        self._safe_update(self.stock_info_text)

        if not material_id:
            return

        self.stock_table.custom_param = {"material_id": material_id}
        self.stock_table.get_data()

        if not self.stock_table.data:
            self.stock_info_text.value = "No stock available for this material."
            self.stock_info_text.visible = True
            self._safe_update(self.stock_info_text)

    def callback_submit(self, e):
        material_id = self.material_dropdown.value if self.material_dropdown else None
        if not material_id:
            self.view.show_error("Select a material first")
            return

        location_ids = []
        qty_outs = []
        remarks_list = []
        for row in self.stock_table.get_rows_with_input_values():
            raw_qty = (row.get("qty_issue") or "").strip()
            if not raw_qty:
                continue
            try:
                qty = float(raw_qty)
            except ValueError:
                self.view.show_error("Qty issue must be a number")
                return
            if qty <= 0:
                continue
            location_ids.append(row.get("location_id"))
            qty_outs.append(raw_qty)
            remarks_list.append(row.get("remarks") or "")

        if not location_ids:
            self.view.show_error("Enter a quantity to issue for at least one location")
            return

        form_data = {
            "stock_out_header_id": self.header_id,
            "material_id": material_id,
            "location_id": location_ids,
            "qty_out": qty_outs,
            "remarks": remarks_list,
        }

        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/submit_items", data=form_data)

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("Stock issued successfully")
        self.page.run_task(
            self.page.push_route, f"/modules/{self.module}/edit/{self.header_id}"
        )

    def _safe_update(self, control):
        try:
            control.update()
        except RuntimeError:
            pass
