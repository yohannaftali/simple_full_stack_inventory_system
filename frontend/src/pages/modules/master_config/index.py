import flet as ft

from components.form.form import Form
from components.module.view import ModuleView


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
                "name": "app_title",
                "label": "Application Title",
                "icon": ft.Icons.TITLE,
                "row": 1,
                "col": {"sm": 12, "md": 6},
                "type": "input",
                "autofocus": True,
            },
            {
                "name": "footer",
                "label": "Footer",
                "icon": ft.Icons.NOTES,
                "row": 2,
                "col": {"sm": 12, "md": 6},
                "type": "input",
            },
            {
                "name": "timezone",
                "label": "Timezone",
                "icon": ft.Icons.SCHEDULE,
                "row": 3,
                "col": {"sm": 12, "md": 6},
                "type": "select",
            },
        ]

        self.form = Form(
            page=page, parent=self, name="index", fields=self.fields, custom_param={}
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Application Config")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        # Singleton settings screens (issue #49) have no "heading" field to
        # give them visual top structure the way a new/edit Form screen's
        # first row often does, and Form.build()'s own padding argument is
        # dead code for vertical spacing (see AGENTS.md) - so this screen
        # (and mail_config/index.py, the only other singleton Form screen)
        # wraps the form in its own top padding instead of relying on a
        # shared default that would also affect every new/edit Form screen.
        return ft.Container(
            content=self.form.build(),
            padding=ft.Padding(top=20, left=0, right=0, bottom=0),
            expand=True,
        )

    def callback_submit(self, e):
        self.form.submit()
