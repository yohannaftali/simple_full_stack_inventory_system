import flet as ft

from components.module.view import ModuleView
from components.form.form import Form
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
                "name": "name", "label": "Name", "icon": ft.Icons.LABEL,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "input", "autofocus": True
            },
            {
                "name": "label", "label": "Label", "icon": ft.Icons.TEXT_FIELDS,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "sort", "label": "Sort", "icon": ft.Icons.SORT,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "icon", "label": "Icon", "icon": ft.Icons.APPS,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "input", "hint_text": "e.g. chevron_right"
            },
            {
                "name": "description", "label": "Description", "icon": ft.Icons.NOTES,
                "row": 3,
                "type": "input"
            }
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="edit",
            fields=self.fields
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Edit Module")

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
        return self.form.build()

    def callback_submit(self, e):
        self.form.submit()

    def callback_delete(self, e):
        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/delete", data={"id": self.record_id})

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        self.view.show_success("Module deleted successfully")
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")
