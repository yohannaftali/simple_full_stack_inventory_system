import flet as ft

from components.module.view import ModuleView
from components.module.view_toggle import ViewToggle
from utils.formatting import format_number
from utils.http_client import HttpClient


class ModulePage:
    """Read-only drill-down from stock_browse/index: current on-hand qty at
    one location, broken down by material, with a totals footer (issue #40 -
    the mirror image of issue #29's stock_by_material.py, scoped the
    opposite way).
    """

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        self.fields = [
            {
                "name": "material_id",
                "type": "hidden", "serialize": False
            },
            {
                "name": "material_code", "label": "Material Code",
                "type": "label", "sort": True
            },
            {
                "name": "material_name", "label": "Material Name",
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

        self.toggle = ViewToggle(
            page=page,
            parent=self,
            name="stock_by_location",
            fields=self.fields,
            list_kwargs={
                "endpoint": f"C_{module}/get_stock_by_location",
                "custom_param": {"location_id": record_id},
            },
            table_kwargs={
                "endpoint": f"C_{module}/get_stock_by_location",
                "custom_param": {"location_id": record_id},
            },
        )

        self.footer_text = ft.Text(self._summarize(), size=14, weight=ft.FontWeight.W_500)

    def _build_title(self) -> str:
        client = HttpClient(self.page)
        response = client.get(f"C_{self.module}/get_location", {"location_id": self.record_id})
        if isinstance(response, dict) and "location_code" in response:
            return f"Stock by Location - {response['location_code']} - {response['location_name']}"
        return "Stock by Location"

    @staticmethod
    def _to_number(value) -> float:
        # Numeric fields arrive over the wire as JSON strings (the backend's
        # SQLAlchemy Decimal columns) - see stock_by_material.py's own
        # _to_number() docstring for the full explanation of why this
        # conversion must happen before summing, not just before display.
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _summarize(self) -> str:
        # Unlike stock_by_material.py's footer (average_price is constant
        # across every row there - one material's own MAP), here EACH row
        # is a different material with its own average_price, so there is
        # no single "the" average price to show - only the totals make
        # sense to aggregate across rows.
        rows = self.toggle.active.data if isinstance(self.toggle.active.data, list) else []
        total_qty = sum(self._to_number(row.get("qty")) for row in rows)
        total_value = sum(self._to_number(row.get("value")) for row in rows)
        return (
            f"Total Qty: {format_number(total_qty)}    "
            f"Total Value: {format_number(total_value)}"
        )

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        return ft.Column(
            controls=[
                ft.Container(content=self.toggle.build(), expand=True),
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
