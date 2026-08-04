import flet as ft

from components.module.view import ModuleView
from components.module.view_toggle import ViewToggle
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

        self.toggle = ViewToggle(
            page=page,
            parent=self,
            name="stock_by_material",
            fields=self.fields,
            list_kwargs={
                "endpoint": f"C_{module}/get_stock_by_material",
                "custom_param": {"material_id": record_id},
            },
            table_kwargs={
                "endpoint": f"C_{module}/get_stock_by_material",
                "custom_param": {"material_id": record_id},
            },
        )

        self.footer_text = ft.Text(self._summarize(), size=14, weight=ft.FontWeight.W_500)

    def _build_title(self) -> str:
        client = HttpClient(self.page)
        response = client.get(f"C_{self.module}/get_material", {"material_id": self.record_id})
        if isinstance(response, dict) and "material_code" in response:
            return f"Stock by Material - {response['material_code']} - {response['material_name']}"
        return "Stock by Material"

    @staticmethod
    def _to_number(value) -> float:
        # Numeric fields arrive over the wire as JSON strings (the backend's
        # SQLAlchemy Decimal columns, e.g. "958.0000") - components/table/rows.py's
        # own "format": "number" display path tolerates this by going
        # through format_number()'s str(value)->float() conversion per cell,
        # but that only formats for display, it doesn't sum. Summing the raw
        # strings directly (`sum(row.get("qty", 0) ...)`) raises TypeError
        # ("unsupported operand type(s) for +: 'int' and 'str'") - which,
        # thrown from inside ModulePage.__init__, module_loader.py's
        # `except TypeError` around the constructor call misreads as "wrong
        # constructor signature" and silently retries the whole page build
        # without record_id, producing a confusing HTTP 422 two GETs later
        # instead of a visible crash here.
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _summarize(self) -> str:
        # List/Table.__init__ already ran get_data() synchronously (not
        # is_inside_form), so self.toggle.active.data is populated by the
        # time this runs - average_price is constant across every row (the
        # material's single MAP, outer-joined in on the backend), so any
        # row's value works; 0 for a material with no current stock at all.
        rows = self.toggle.active.data if isinstance(self.toggle.active.data, list) else []
        total_qty = sum(self._to_number(row.get("qty")) for row in rows)
        total_value = sum(self._to_number(row.get("value")) for row in rows)
        average_price = self._to_number(rows[0].get("average_price")) if rows else 0.0
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
