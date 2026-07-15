"""Module-access checklist shown on the user edit screen (ap_master_user).

Lets an admin grant/revoke which modules a given user can see, backed by
C_ap_master_user/get_all_modules, get_permissions and save_permissions.
"""

import flet as ft

from utils.http_client import HttpClient


class PermissionChecklist:
    """Checklist of modules to grant/revoke access for a user."""

    def __init__(self, page: ft.Page, user_id: str | int):
        self.page = page
        self.user_id = user_id
        self.checkboxes: dict[str, ft.Checkbox] = {}
        self.list_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=250)
        self.status_text = ft.Text("", size=12, visible=False)

    def build(self) -> ft.Control:
        self._load()
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Module Access", size=14, weight=ft.FontWeight.BOLD),
                    self.list_column,
                    self.status_text,
                    ft.Button(
                        content="Save Permissions",
                        icon=ft.Icons.SAVE,
                        on_click=self.on_save_click,
                        bgcolor=ft.Colors.SECONDARY,
                        color=ft.Colors.ON_SECONDARY,
                    ),
                ],
                spacing=10,
            ),
            padding=ft.Padding.Symmetric(horizontal=20, vertical=10),
        )

    def _load(self):
        client = HttpClient(self.page)
        modules_response = client.get("C_ap_master_user/get_all_modules")
        granted_response = client.get(
            "C_ap_master_user/get_permissions", {"id": self.user_id}
        )

        granted_ids = set()
        if isinstance(granted_response, dict) and isinstance(
            granted_response.get("module_ids"), list
        ):
            granted_ids = {
                str(module_id) for module_id in granted_response["module_ids"]
            }

        self.checkboxes = {}
        self.list_column.controls = []
        if isinstance(modules_response, list):
            for module in modules_response:
                module_id = str(module.get("id"))
                checkbox = ft.Checkbox(
                    label=module.get("label", module.get("name", module_id)),
                    value=module_id in granted_ids,
                )
                self.checkboxes[module_id] = checkbox
                self.list_column.controls.append(checkbox)

    def rebuild(self):
        """Re-fetch and re-render (called after Form.build() like other list/table fields)."""
        self._load()
        try:
            self.list_column.update()
        except RuntimeError:
            pass

    def on_save_click(self, e):
        selected_ids = [
            module_id
            for module_id, checkbox in self.checkboxes.items()
            if checkbox.value
        ]
        client = HttpClient(self.page)
        response = client.post(
            "C_ap_master_user/save_permissions",
            data={"user_id": self.user_id, "module_ids": ",".join(selected_ids)},
        )

        if isinstance(response, dict) and "error" in response:
            self.status_text.value = response["error"]
            self.status_text.color = ft.Colors.ERROR
        else:
            self.status_text.value = "Permissions saved"
            self.status_text.color = ft.Colors.PRIMARY
        self.status_text.visible = True
        try:
            self.status_text.update()
        except RuntimeError:
            pass
