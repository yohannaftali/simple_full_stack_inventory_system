"""Grant module access to a user (issue #41).

`record_id` here is the *user* id, not a permission-grant id - route:
/modules/ap_master_user/permission_new/<user_id>. Lists, via the shared
`components/table/table.py` Table (paginated, filterable using the same
generic per-column filter convention as every other table), every module
the user does NOT yet have access to (C_ap_master_user/get_ungranted_modules),
each row with a checkbox column. Checking one or more rows and pressing
Submit reads them back via `Table.get_rows_with_input_values()` and posts
the checked module ids to C_ap_master_user/submit_permission_new - additive
only, existing grants are untouched - then returns to the user's edit
screen, where the granted-modules table (`permission_table.py`) now
reflects the new grants.
"""

import flet as ft

from components.module.view import ModuleView
from components.table.table import Table
from utils.http_client import HttpClient


class ModulePage:
    """Module screen class"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.user_id = record_id
        self.record_id = record_id

        self.fields = [
            {
                "name": "id",
                "type": "hidden"
            },
            {
                "name": "name", "label": "Module",
                "type": "label", "sort": True
            },
            {
                "name": "label", "label": "Label",
                "type": "label", "sort": True
            },
            {
                "name": "description", "label": "Description",
                "type": "label", "sort": True
            },
            {
                "name": "module_group_name", "label": "Group",
                "type": "label", "sort": True
            },
            {
                "name": "selected", "label": "Select",
                "type": "checkbox", "filter": False
            }
        ]

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Add Permission")

        self.table = Table(
            page=page,
            parent=self,
            name="ungranted_modules",
            fields=self.fields,
            custom_param={"id": self.user_id},
        )

        self.table.toolbar.add_save_button(
            callback=self.callback_submit,
            icon=ft.Icons.CHECK,
            tooltip="Submit",
        )

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.table.build()

    def callback_submit(self, e):
        module_ids = [
            row.get("id")
            for row in self.table.get_rows_with_input_values()
            if row.get("selected")
        ]
        if not module_ids:
            self.view.show_error("Select at least one module")
            return

        client = HttpClient(self.page)
        response = client.post(
            f"C_{self.module}/submit_permission_new",
            data={"user_id": self.user_id, "module_ids": module_ids},
        )

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("Permission added successfully")
        self.page.run_task(
            self.page.push_route, f"/modules/{self.module}/edit/{self.user_id}"
        )
