"""Granted-module-access sub-table embedded in a user's edit screen, built
on the shared `components/table/table.py` (paginated list/search, filterable
via the existing generic per-column filter convention) - same wrapper shape
as `stock_in/item_table.py`. Granting new access happens on the separate
`permission_new.py` screen, reached via this table's own "Add Permission"
toolbar button; revoking access happens directly here via the shared
single/bulk row-remove column (issue #42, components/table/remove.py),
wired to C_ap_master_user/revoke_permission.
"""

import flet as ft

from components.table.table import Table
from utils.http_client import HttpClient


class PermissionTable:
    """Granted-module list for a user, with an "Add Permission" button."""

    def __init__(self, page: ft.Page, parent, module: str, user_id: str | int):
        self.page = page
        self.parent = parent  # the user's edit ModulePage
        self.module = module
        self.screen = f"{parent.screen}_permissions"
        self.user_id = user_id

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
            }
        ]

        self.table = Table(
            page=page,
            parent=self,
            name="granted_modules",
            fields=self.fields,
            custom_param={"id": user_id},
            fill_available_space=False,
            on_remove_row=self._revoke_module,
            on_remove_rows=self._revoke_modules,
        )

        self.table.toolbar.add_new_button(
            callback=self.callback_add_permission,
            icon=ft.Icons.ADD_MODERATOR,
            tooltip="Add Permission",
        )

    @property
    def view(self):
        """Delegate to the user edit page's view - Table.get_data() calls
        `self.parent.view.show_error(...)` on load failure."""
        return self.parent.view

    def build(self) -> ft.Control:
        return self.table.build()

    def callback_add_permission(self, e):
        self.page.run_task(
            self.page.push_route,
            f"/modules/{self.module}/permission_new/{self.user_id}",
        )

    def _revoke_module(self, row: dict) -> str | None:
        return self._revoke_modules([row])

    def _revoke_modules(self, rows: list[dict]) -> str | None:
        client = HttpClient(self.page)
        response = client.post(
            f"C_{self.module}/revoke_permission",
            data={"user_id": self.user_id, "module_ids": [row.get("id") for row in rows]},
        )
        if isinstance(response, dict) and "error" in response:
            return response["error"]
        return None
