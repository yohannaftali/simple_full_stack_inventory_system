import flet as ft

from components.module.view import ModuleView
from components.form.form import Form


class ModulePage:
    """Singleton application config screen - no list/new/edit split, this
    screen itself is the settings form (get/submit against the one
    app_configs row)."""

    def __init__(self, page: ft.Page, module: str, screen=str):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = None

        self.fields = [
            {
                "name": "app_title", "label": "Application Title", "icon": ft.Icons.TITLE,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "input", "autofocus": True
            },
            {
                "name": "footer", "label": "Footer", "icon": ft.Icons.NOTES,
                "row": 2,
                "type": "input"
            },
            {
                "name": "timezone", "label": "Timezone", "icon": ft.Icons.SCHEDULE,
                "row": 3, "col": {"sm": 12, "md": 6},
                "type": "select"
            }
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="index",
            fields=self.fields,
            custom_param={}
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Application Config")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        self.form.submit()
