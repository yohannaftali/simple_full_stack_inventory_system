"""Read/navigate item sub-table embedded in a receiving header's edit screen.

Not built on components/table/table.py: that component's row click always
navigates to `/modules/{module}/edit/{id}`, which would collide with this
same module's header edit screen (`edit/<header_id>` vs. wanting
`item_edit/<item_id>`). A plain DataTable with a custom on-click sidesteps
that instead of fighting the shared component.
"""

import flet as ft

from utils.http_client import HttpClient


class ItemTable:
    """Item sub-table for a receiving header, with an "Add Item" button."""

    def __init__(self, page: ft.Page, module: str, header_id: str | int):
        self.page = page
        self.module = module
        self.header_id = header_id
        self.data: list = []

    def build(self) -> ft.Control:
        self._load()

        rows = []
        for item in self.data:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.get("material_code", ""))),
                        ft.DataCell(ft.Text(item.get("material_name", ""))),
                        ft.DataCell(ft.Text(item.get("location_code", ""))),
                        ft.DataCell(ft.Text(str(item.get("qty_received", "")))),
                        ft.DataCell(ft.Text(str(item.get("price_buy", "")))),
                        ft.DataCell(ft.Text(item.get("remarks", ""))),
                    ],
                    on_select_change=self._make_on_click(item["id"]),
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Material Code")),
                ft.DataColumn(ft.Text("Material")),
                ft.DataColumn(ft.Text("Location")),
                ft.DataColumn(ft.Text("Qty")),
                ft.DataColumn(ft.Text("Price")),
                ft.DataColumn(ft.Text("Remarks")),
            ],
            rows=rows,
        )

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Items", weight=ft.FontWeight.BOLD, size=16),
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            tooltip="Add item",
                            on_click=self._on_add_click,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=table,
                    padding=ft.Padding.only(top=5),
                ),
            ],
            spacing=5,
        )

    def _load(self):
        client = HttpClient(self.page)
        response = client.get(f"C_{self.module}/get_items", {"header_id": self.header_id})
        if isinstance(response, list):
            self.data = response

    def _make_on_click(self, item_id):
        def handler(e):
            self.page.run_task(
                self.page.push_route, f"/modules/{self.module}/item_edit/{item_id}"
            )

        return handler

    def _on_add_click(self, e):
        self.page.run_task(
            self.page.push_route, f"/modules/{self.module}/item_new/{self.header_id}"
        )
