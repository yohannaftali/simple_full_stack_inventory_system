import flet as ft

from components.module.view import ModuleView
from components.form.form import Form


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
                "key": True
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
            },
            {
                "name": "is_active", "label": "Active", "icon": ft.Icons.CHECK_CIRCLE,
                "row": 3, "col": {"sm": 12, "md": 6},
                "type": "select"
            }
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="new",
            fields=self.fields,
            start_blank=True
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("New Material")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        self.form.submit()
