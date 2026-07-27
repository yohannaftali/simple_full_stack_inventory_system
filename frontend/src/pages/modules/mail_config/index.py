import flet as ft

from components.module.view import ModuleView
from components.form.form import Form


class ModulePage:
    """Singleton mail/SMTP config screen - no list/new/edit split, this
    screen itself is the settings form (get/submit against the one
    mail_configs row)."""

    def __init__(self, page: ft.Page, module: str, screen=str):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = None

        self.fields = [
            {
                "name": "smtp_host", "label": "SMTP Host", "icon": ft.Icons.DNS,
                "row": 1, "col": {"sm": 12, "md": 8},
                "type": "input", "autofocus": True
            },
            {
                "name": "smtp_port", "label": "SMTP Port", "icon": ft.Icons.SETTINGS_ETHERNET,
                "row": 1, "col": {"sm": 12, "md": 4},
                "type": "input"
            },
            {
                "name": "smtp_username", "label": "SMTP Username", "icon": ft.Icons.PERSON,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "smtp_password", "label": "SMTP Password", "icon": ft.Icons.LOCK,
                "row": 2, "col": {"sm": 12, "md": 6},
                "type": "input", "password": True
            },
            {
                "name": "sender_name", "label": "Sender Name", "icon": ft.Icons.BADGE,
                "row": 3, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "sender_email", "label": "Sender Email", "icon": ft.Icons.EMAIL,
                "row": 3, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": "use_tls", "label": "Use TLS", "icon": ft.Icons.LOCK_OUTLINE,
                "row": 4, "col": {"sm": 12, "md": 6},
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
        self.view.header.set_title("Mail Config")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        # Singleton settings screens (issue #49) have no "heading" field to
        # give them visual top structure the way a new/edit Form screen's
        # first row often does, and Form.build()'s own padding argument is
        # dead code for vertical spacing (see AGENTS.md) - so this screen
        # (and master_config/index.py, the only other singleton Form screen)
        # wraps the form in its own top padding instead of relying on a
        # shared default that would also affect every new/edit Form screen.
        return ft.Container(
            content=self.form.build(),
            padding=ft.Padding(top=20, left=0, right=0, bottom=0),
            expand=True,
        )

    def callback_submit(self, e):
        self.form.submit()
