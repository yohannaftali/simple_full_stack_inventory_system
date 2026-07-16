import flet as ft

from components.module.view import ModuleView
from components.form.form import Form
from utils.http_client import HttpClient


class ModulePage:
    """Module screen class"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
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
                "name": "material_code", "label": "Code", "icon": ft.Icons.QR_CODE,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "input", "autofocus": True
            },
            {
                "name": "material_name", "label": "Name", "icon": ft.Icons.LABEL,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "unit_id", "label": "Unit", "icon": ft.Icons.STRAIGHTEN,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": "category_id", "label": "Category", "icon": ft.Icons.CATEGORY,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "select"
            }
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="edit",
            fields=self.fields
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Edit Material")

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
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        self.form.submit()

    def callback_delete(self, e):
        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/delete", data={"id": self.record_id})

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("Material deleted successfully")
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")
