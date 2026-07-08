import flet as ft
from components.module.view import ModuleView
from components.form.form import Form


class ModulePage:
    """Module screen class"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        """
        Initialize Module Page

        Args:
            page: The Flet page
            module: string
            screen: string
            record_id: string | int
        """
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        self.fields_table_list_vin = [
            {
                "name": "item_id",
                "type": "hidden", "key": True
            },
            {
                "name": "vin_no",
                "position": "title"
            },
            {
                "name": "inbound_datetime", "label": "Inbound",
                "position": "leading", "row": 0
            },
            {
                "name": "inbound_by",
                "position": "leading", "row": 1
            },
            {
                "name": "outbound_datetime", "label": "Outbound",
                "position": "trailing", "row": 0
            },
            {
                "name": "outbound_by",
                "position": "trailing", "row": 1
            },
            {
                "name": "remarks_view",
                "position": "subtitle", "row": 0
            },
            {
                "name": "remarks",
                "position": "subtitle", "row": 1
            },
        ]

        self.fields = [
            {
                "name": "dn_number",
                "type": "hidden", "key": True
            },
            {
                "name": 'l1', "label": 'Inbound', "icon": ft.Icons.AIRPLANE_TICKET,
                "row": 10, "col": {"sm": 12},
                "type": "heading"
            },
            {
                "name": "dn_number", "label": "DN Number", "icon": ft.Icons.NUMBERS,
                "row": 11, "col": {"sm": 12, "md": 6},
                "type": "label"
            },
            {
                "name": "out_date", "label": "Issue Date", "icon": ft.Icons.DATE_RANGE,
                "row": 11, "col": {"sm": 12, "md": 6},
                "type": "label"},
            {
                "name": "license_plate", "label": "License No", "icon": ft.Icons.ABC,
                "row": 12, "col": {"sm": 12, "md": 6},
                "type": "label"
            },
            {
                "name": "driver_name", "label": "Driver Name", "icon": ft.Icons.ABC,
                "row": 12, "col": {"sm": 12, "md": 6},
                "type": "label"
            },
            {
                "name": "origin", "label": "Origin", "icon": ft.Icons.ABC,
                "row": 13,  "col": {"sm": 12, "md": 6},
                "type": "label"
            },
            {
                "name": "destination",  "label": "Destination", "icon": ft.Icons.ABC,
                "row": 13, "col": {"sm": 12, "md": 6},
                "type": "label"
            },
            {
                "name": "count_cbu", "label": "Total CBU", "icon": ft.Icons.ABC,
                "row": 14,
                "type": "label"
            },
            {
                "name": 'l2', "label": 'Current', "icon": ft.Icons.ANNOUNCEMENT,
                "row": 20, "col": {"sm": 12},
                "type": "heading"
            },
            {
                "name": "status", "label": "Status", "icon": ft.Icons.ABC,
                "row": 21,
                "type": "label"
            },
            {
                "name": "inbound_time",  "label": "Inbound Time", "icon": ft.Icons.ABC,
                "row": 22,
                "type": "label"
            },
            {
                "name": "table_list_vin", "label": "VIN List", "icon": ft.Icons.CAR_RENTAL,
                "row": 90,
                "type": "list",
                "content": self.fields_table_list_vin
            },
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="edit",
            fields=self.fields
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Edit Config")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        self.form.submit()
