import flet as ft

from components.form.date import DateForm
from components.module.view import ModuleView
from components.table.table import Table


class ModulePage:
    """Read-only material usage/cost by department report, optionally
    narrowed to a date range (issue #9 - reuses #8's `{field}-filter`
    convention and standalone-`DateForm` UI pattern)."""

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

        self.fields = [
            {
                "name": "department_id",
                "type": "hidden", "serialize": False
            },
            {
                "name": "department_code", "label": "Dept Code",
                "type": "label", "sort": True
            },
            {
                "name": "department_name", "label": "Department",
                "type": "label", "sort": True
            },
            {
                "name": "material_code", "label": "Material Code",
                "type": "label", "sort": True
            },
            {
                "name": "material_name", "label": "Material",
                "type": "label", "sort": True
            },
            {
                "name": "total_qty_out", "label": "Total Qty",
                "type": "label", "format": "number", "sort": True
            },
            {
                "name": "unit_name", "label": "Unit",
                "type": "label", "sort": True
            },
            {
                "name": "total_cost", "label": "Total Cost",
                "type": "label", "format": "number", "sort": True
            }
        ]

        self.view = ModuleView(page, module, screen)

        self.table = Table(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields
        )

        self.view.toolbar.add_button(
            position="right",
            callback=self.callback_apply_filters,
            icon=ft.Icons.FILTER_ALT,
            tooltip="Apply Filters",
        )

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
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
                ft.Container(content=self.table.build(), expand=True),
            ],
            expand=True,
        )

    def callback_apply_filters(self, e):
        self.table.custom_param = {
            "start_date-filter": self.start_date_form.get_value(),
            "end_date-filter": self.end_date_form.get_value(),
        }
        self.table.page_number = 1
        self.table.get_data()
