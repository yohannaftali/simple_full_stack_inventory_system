"""Granted-module-access sub-table embedded in a user's edit screen, built
on the shared `components/table/table.py` (paginated list/search, filterable
via the existing generic per-column filter convention) - same wrapper shape
as `stock_in/item_table.py`. Read-only display only; granting new access
happens on the separate `permission_new.py` screen, reached via this
table's own "Add Permission" toolbar button.
"""

import flet as ft

from components.table.table import Table


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
