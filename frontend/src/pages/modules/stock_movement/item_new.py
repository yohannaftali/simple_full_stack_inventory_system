import flet as ft

from components.module.view import ModuleView
from components.table.table import Table
from utils.http_client import HttpClient


class ModulePage:
    """Transfer stock against a header.

    `record_id` here is the *stock movement header* id (route:
    /modules/stock_movement/item_new/<header_id>), not an item id -
    transferring is create-only.

    Same hand-built shape as `stock_out/item_new.py`: picking a material
    loads a shared `components/table/table.py` Table (against
    C_stock_movement/get_stock_by_material) with one row per location
    currently holding stock of that material - these rows are the
    *origin* locations. A single **Destination Location** dropdown (fed by
    C_stock_movement/call_location_id_select) applies to every row
    submitted from this screen, since a stock_movement_item needs exactly
    one destination but the origin-location table can span several rows.
    The "Qty Movement"/"Remarks" columns are `"type": "input"` fields -
    same editable-cell mechanism `stock_out/item_new.py` uses for its own
    "Qty Issue" column - and `Table.get_rows_with_input_values()` reads
    back what the user typed. Submitting posts one
    stock_movement_header_id/material_id/destination_location_id triplet
    plus a repeated origin_location_id/movement_qty/remarks triplet per row
    with a qty > 0 (C_stock_movement/submit_items) - the backend creates
    one stock_movement_item per origin location, each deducted FIFO within
    that location and re-added as a new lot at the destination.

    Unlike stock_out/item_new.py, there is no separate multi-material bulk
    endpoint here - the origin-location table below is a plain
    `is_inside_form=True` Table with editable columns, so it already gets a
    generic CSV/XLSX upload menu for free (see AGENTS.md's "Table
    export/upload convention"), matching rows by Location (code or
    "CODE - Name") and filling Qty Movement/Remarks - no bespoke bulk
    endpoint needed for that flow.
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
        self.location_options: list = []
        self.material_dropdown: ft.Dropdown | None = None
        self.destination_dropdown: ft.Dropdown | None = None
        self.stock_info_text = ft.Text("", size=12, visible=False)

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Move Stock")
        self.view.toolbar.add_submit_button(callback=self.callback_submit)

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
                    "name": "qty_movement",
                    "label": "Qty Movement",
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
        self._load_location_options()

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

        self.destination_dropdown = ft.Dropdown(
            label="Destination Location",
            hint_text="Select a destination location",
            leading_icon=ft.Icon(ft.Icons.PLACE),
            border_radius=10,
            options=[
                ft.DropdownOption(key=opt.get("value", ""), text=opt.get("label", ""))
                for opt in self.location_options
            ],
            expand=True,
        )

        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.ResponsiveRow(
                        controls=[
                            ft.Container(content=self.material_dropdown, col={"sm": 12, "md": 6}),
                            ft.Container(
                                content=self.destination_dropdown, col={"sm": 12, "md": 6}
                            ),
                        ]
                    ),
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

    def _load_location_options(self):
        client = HttpClient(self.page)
        response = client.get(f"C_{self.module}/call_location_id_select")
        if isinstance(response, list):
            self.location_options = response

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

        destination_location_id = (
            self.destination_dropdown.value if self.destination_dropdown else None
        )
        if not destination_location_id:
            self.view.show_error("Select a destination location first")
            return

        origin_location_ids = []
        movement_qtys = []
        remarks_list = []
        for row in self.stock_table.get_rows_with_input_values():
            raw_qty = (row.get("qty_movement") or "").strip()
            if not raw_qty:
                continue
            try:
                qty = float(raw_qty)
            except ValueError:
                self.view.show_error("Qty movement must be a number")
                return
            if qty <= 0:
                continue
            origin_location_id = row.get("location_id")
            if str(origin_location_id) == str(destination_location_id):
                self.view.show_error("Origin and destination location cannot be the same")
                return
            origin_location_ids.append(origin_location_id)
            movement_qtys.append(raw_qty)
            remarks_list.append(row.get("remarks") or "")

        if not origin_location_ids:
            self.view.show_error("Enter a quantity to move for at least one location")
            return

        form_data = {
            "stock_movement_header_id": self.header_id,
            "material_id": material_id,
            "destination_location_id": destination_location_id,
            "origin_location_id": origin_location_ids,
            "movement_qty": movement_qtys,
            "remarks": remarks_list,
        }

        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/submit_items", data=form_data)

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("Stock moved successfully")
        self.page.run_task(
            self.page.push_route, f"/modules/{self.module}/edit/{self.header_id}"
        )

    def _safe_update(self, control):
        try:
            control.update()
        except RuntimeError:
            pass
