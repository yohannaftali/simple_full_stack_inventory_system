import flet as ft

from components.module.view import ModuleView
from components.table.table import Table
from utils.formatting import format_number
from utils.http_client import HttpClient


class ModulePage:
    """Read-only drill-down from stock_browse/index: current on-hand qty for
    one material, broken down by location, with a totals footer (issue #29).
    """

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        self.fields = [
            {
                "name": "location_id",
                "type": "hidden", "serialize": False
            },
            {
                "name": "location_code", "label": "Location Code",
                "type": "label", "sort": True
            },
            {
                "name": "location_name", "label": "Location",
                "type": "label", "sort": True
            },
            {
                "name": "qty", "label": "Qty",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "unit_name", "label": "Unit",
                "type": "label", "sort": True
            },
            {
                "name": "average_price", "label": "Avg Price",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "value", "label": "Value",
                "type": "label", "format": "number", "sort": True
            }
        ]

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title(self._build_title())

        self.table = Table(
            page=page,
            parent=self,
            name="stock_by_material",
            fields=self.fields,
            endpoint=f"C_{module}/get_stock_by_material",
            custom_param={"material_id": record_id},
        )

        self.footer_text = ft.Text(self._summarize(), size=14, weight=ft.FontWeight.W_500)

    def _build_title(self) -> str:
        client = HttpClient(self.page)
        response = client.get(f"C_{self.module}/get_material", {"material_id": self.record_id})
        if isinstance(response, dict) and "material_code" in response:
            return f"Stock by Material - {response['material_code']} - {response['material_name']}"
        return "Stock by Material"

    def _summarize(self) -> str:
        # Table.__init__ already ran get_data() synchronously (not
        # is_inside_form), so self.table.data is populated by the time this
        # runs - average_price is constant across every row (the material's
        # single MAP, outer-joined in on the backend), so any row's value
        # works; 0 for a material with no current stock at all.
        rows = self.table.data if isinstance(self.table.data, list) else []
        total_qty = sum(row.get("qty", 0) or 0 for row in rows)
        total_value = sum(row.get("value", 0) or 0 for row in rows)
        average_price = rows[0].get("average_price", 0) if rows else 0
        return (
            f"Total Qty: {format_number(total_qty)}    "
            f"MAP: {format_number(average_price)}    "
            f"Total Value: {format_number(total_value)}"
        )

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        return ft.Column(
            controls=[
                ft.Container(content=self.table.build(), expand=True),
                ft.Container(
                    content=self.footer_text,
                    padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                    alignment=ft.Alignment.CENTER_RIGHT,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                ),
            ],
            expand=True,
            spacing=0,
        )
