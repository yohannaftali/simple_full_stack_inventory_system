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
                "name": "date", "label": "Date", "icon": ft.Icons.EVENT,
                "row": 1,
                "type": "date", "autofocus": True
            },
            {
                "name": "description", "label": "Description", "icon": ft.Icons.NOTES,
                "row": 2,
                "type": "input"
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
        self.view.header.set_title("New Receiving")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        self.form.submit()
