import flet as ft

from components.module.view import ModuleView
from components.form.form import Form
from pages.modules.ap_master_user.permission_checklist import PermissionChecklist
from utils.http_client import HttpClient


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

        self.fields = [
            {
                "name": "id", "type": "hidden",
                "key": True,
            },
            {
                "name": "username", "label": "Username", "icon": ft.Icons.PERSON,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "input", "autofocus": True
            },
            {
                "name": "email", "label": "Email", "icon": ft.Icons.EMAIL,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "password", "label": "Password (leave blank to keep)", "icon": ft.Icons.LOCK,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "is_active", "label": "Active", "icon": ft.Icons.CHECK_CIRCLE,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": "is_superuser", "label": "Superuser", "icon": ft.Icons.ADMIN_PANEL_SETTINGS,
                "row": 3, "col": {"sm": 12, "md": 6},
                "type": "select"
            }
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="edit",
            fields=self.fields
        )
        self.permission_checklist = (
            PermissionChecklist(page, record_id) if record_id else None
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Edit User")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)
        self.view.toolbar.add_button(
            position="left",
            callback=self.callback_delete,
            icon=ft.Icons.DELETE,
            tooltip="Delete",
            bgcolor=ft.Colors.ERROR,
            icon_color=ft.Colors.ON_ERROR,
        )

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body())

    def body(self):
        controls = [self.form.build()]
        if self.permission_checklist is not None:
            controls.append(self.permission_checklist.build())
        return ft.Column(controls=controls, expand=True, scroll=ft.ScrollMode.AUTO)

    def callback_submit(self, e):
        self.form.submit()

    def callback_delete(self, e):
        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/delete", data={"id": self.record_id})

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("User deleted successfully")
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")
