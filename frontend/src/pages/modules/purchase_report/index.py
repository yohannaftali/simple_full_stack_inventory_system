import flet as ft

from components.form.date import DateForm
from components.module.view import ModuleView
from components.table.table import Table
from utils.http_client import HttpClient


class ModulePage:
    """Read-only purchase report: total purchase by supplier and by
    material, both grouped tables sharing one date-range filter above them,
    each additionally narrowable by its own supplier/material select
    (blank/"All" = no scoping on that dimension - the existing grouped
    breakdown). Filters apply on demand via the toolbar's "Apply Filters"
    button, not per-keystroke/per-select, since `DateForm` has no
    on_change hook to wire live updates through.
    """

    def __init__(self, page: ft.Page, module: str, screen=str):
        self.page = page
        self.module = module
        self.screen = screen

        self.start_date_form = DateForm(
            page, self, {"name": "start_date", "label": "Start Date", "icon": ft.Icons.EVENT}
        )
        self.end_date_form = DateForm(
            page, self, {"name": "end_date", "label": "End Date", "icon": ft.Icons.EVENT}
        )

        self.supplier_options: list = []
        self.material_options: list = []
        self.supplier_dropdown: ft.Dropdown | None = None
        self.material_dropdown: ft.Dropdown | None = None

        self.view = ModuleView(page, module, screen)

        by_supplier_fields = [
            {"name": "supplier_id", "type": "hidden", "serialize": False},
            {"name": "supplier_code", "label": "Code", "type": "label", "sort": True},
            {"name": "supplier_name", "label": "Supplier", "type": "label", "sort": True},
            {
                "name": "total_qty", "label": "Total Qty",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "total_purchase", "label": "Total Purchase",
                "type": "label", "format": "number", "sort": True
            },
        ]
        by_material_fields = [
            {"name": "material_id", "type": "hidden", "serialize": False},
            {"name": "material_code", "label": "Code", "type": "label", "sort": True},
            {"name": "material_name", "label": "Material", "type": "label", "sort": True},
            {
                "name": "total_qty", "label": "Total Qty",
                "type": "label", "format": "number", "sort": True
            },
            {"name": "unit_name", "label": "Unit", "type": "label", "sort": True},
            {
                "name": "total_purchase", "label": "Total Purchase",
                "type": "label", "format": "number", "sort": True
            },
        ]

        self.by_supplier_table = Table(
            page=page, parent=self, name="by_supplier", fields=by_supplier_fields,
            fill_available_space=False,
        )
        self.by_material_table = Table(
            page=page, parent=self, name="by_material", fields=by_material_fields,
            fill_available_space=False,
        )

        self._load_filter_options()

        self.view.toolbar.add_button(
            position="right",
            callback=self.callback_apply_filters,
            icon=ft.Icons.FILTER_ALT,
            tooltip="Apply Filters",
        )

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        self.supplier_dropdown = ft.Dropdown(
            label="Supplier",
            hint_text="All Suppliers",
            leading_icon=ft.Icon(ft.Icons.LOCAL_SHIPPING),
            border_radius=10,
            options=[
                ft.DropdownOption(key=opt.get("value", ""), text=opt.get("label", ""))
                for opt in self.supplier_options
            ],
            expand=True,
        )
        self.material_dropdown = ft.Dropdown(
            label="Material",
            hint_text="All Materials",
            leading_icon=ft.Icon(ft.Icons.INVENTORY_2),
            border_radius=10,
            options=[
                ft.DropdownOption(key=opt.get("value", ""), text=opt.get("label", ""))
                for opt in self.material_options
            ],
            expand=True,
        )

        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                content=self.start_date_form.build(), col={"sm": 12, "md": 6}
                            ),
                            ft.Container(
                                content=self.end_date_form.build(), col={"sm": 12, "md": 6}
                            ),
                        ]
                    ),
                    padding=ft.Padding.symmetric(horizontal=20, vertical=10),
                ),
                ft.Container(
                    content=ft.Text("By Supplier", weight=ft.FontWeight.BOLD, size=16),
                    padding=ft.Padding.only(left=20, right=20, top=10),
                ),
                ft.Container(
                    content=self.supplier_dropdown,
                    padding=ft.Padding.symmetric(horizontal=20, vertical=10),
                ),
                ft.Container(content=self.by_supplier_table.build(), height=350),
                ft.Container(
                    content=ft.Text("By Material", weight=ft.FontWeight.BOLD, size=16),
                    padding=ft.Padding.only(left=20, right=20, top=10),
                ),
                ft.Container(
                    content=self.material_dropdown,
                    padding=ft.Padding.symmetric(horizontal=20, vertical=10),
                ),
                ft.Container(content=self.by_material_table.build(), height=350),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _load_filter_options(self):
        client = HttpClient(self.page)
        supplier_response = client.get(f"C_{self.module}/call_supplier_id_select")
        if isinstance(supplier_response, list):
            self.supplier_options = supplier_response
        material_response = client.get(f"C_{self.module}/call_material_id_select")
        if isinstance(material_response, list):
            self.material_options = material_response

    def callback_apply_filters(self, e):
        start_date = self.start_date_form.get_value()
        end_date = self.end_date_form.get_value()
        supplier_id = self.supplier_dropdown.value if self.supplier_dropdown else ""
        material_id = self.material_dropdown.value if self.material_dropdown else ""

        self.by_supplier_table.custom_param = {
            "start_date-filter": start_date,
            "end_date-filter": end_date,
            "supplier_id-filter": supplier_id or "",
        }
        self.by_material_table.custom_param = {
            "start_date-filter": start_date,
            "end_date-filter": end_date,
            "material_id-filter": material_id or "",
        }
        self.by_supplier_table.page_number = 1
        self.by_material_table.page_number = 1
        self.by_supplier_table.get_data()
        self.by_material_table.get_data()
