import flet as ft

from components.module.view import ModuleView
from components.list.list import List
from utils.http_client import HttpClient


class ModulePage:
    """Page 1 — PR list for mobile stock picking (#628)."""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id
        self.department_id = ""

        self.fields = [
            {"name": "request_header_id", "type": "hidden"},
            {"name": "request_date", "icon": ft.Icons.DATE_RANGE, "position": "leading", "row": 0},
            {"name": "request_no", "position": "title"},
            {"name": "remarks", "position": "subtitle", "row": 0},
        ]

        self.view = ModuleView(page, module, screen)

        # Endpoint kept clean; department_id is injected by the get_data override below.
        self.list = List(
            page=page,
            parent=self,
            name="stock_picking_list",
            fields=self.fields,
            endpoint=f"C_{module}/get_stock_picking_list",
        )

        # Route to the detail (picking) screen instead of the default edit route.
        self._original_tiles_load = self.list.tiles.load
        self.list.tiles.load = self._custom_tiles_load

        # Inject department_id into every fetch (List's URL builder only carries the keyword).
        self.list.get_data = self._fetch_list

        self._add_department_toolbar()

    # ---- Department filter -------------------------------------------------
    def _add_department_toolbar(self):
        options = self._get_department_options()
        self.department_dropdown = ft.Dropdown(
            label="Department",
            value=None,
            options=[ft.dropdown.Option(text="All", key="")] + [
                ft.dropdown.Option(text=o.get("label", ""), key=str(o.get("value", "")))
                for o in options if str(o.get("value", "")) != ""
            ],
            on_select=self._on_department_change,
            dense=True,
            width=200,
        )
        self.list.toolbar.right = self.list.toolbar.right or []
        self.list.toolbar.right.insert(0, self.department_dropdown)

    def _get_department_options(self):
        client = HttpClient(self.page)
        response = client.get(f"C_{self.module}/call_department_select")
        return response if isinstance(response, list) else []

    def _on_department_change(self, e):
        if not self.department_dropdown.value:
            return
        self.department_id = self.department_dropdown.value
        self.list.page_number = 1
        self.list.get_data()

    # ---- Data fetch with department_id ------------------------------------
    def _fetch_list(self, page_no: int = 1, offset: int = 0, append: bool = False):
        lst = self.list
        lst.data = []
        client = HttpClient(self.page)
        parts = []
        if self.department_id:
            parts.append(f"department_id={self.department_id}")
        if lst.filter:
            parts.append(f"table-keyword-filter={lst.filter}")
        parts += [f"limit={lst.limit}", f"page={page_no}", f"offset={offset}"]
        response = client.get(f"{lst.endpoint}?{'&'.join(parts)}")

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(f"Failed to load data: {response.get('error')}")
            return

        if isinstance(response, list) and len(response) > 0:
            first = response[0]
            lst.total_pages = first.get("db_total_page", 1)
            lst.total_rows = first.get("db_num_rows", len(response))
            lst.data = response
            lst.load(response, append=append)
        else:
            lst.data = []
            lst.load([], append=False)

    # ---- Tile navigation ---------------------------------------------------
    def _custom_tiles_load(self, data: list, append: bool = False):
        self._original_tiles_load(data, append)
        for i, tile in enumerate(self.list.tiles.tiles):
            if i < len(data):
                record = data[i] if not append else data[i - (len(self.list.tiles.tiles) - len(data))]
                hid = record.get("request_header_id", "")
                tile.trailing = ft.IconButton(
                    icon=ft.Icons.ARROW_FORWARD_IOS,
                    icon_size=16,
                    tooltip="Pick Items",
                    on_click=lambda e, h=hid: self.page.run_task(self.page.push_route, f"/modules/{self.module}/detail/{h}"),
                )

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.list.build()
