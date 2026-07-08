import flet as ft

from utils.http_client import HttpClient
from components.module.view import ModuleView
from components.form.form import Form


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
                "name": 'l1', "label": 'Connection', "icon": ft.Icons.NETWORK_CELL,
                "row": 10, "col": {"sm": 12},
                "type": "heading"
            },
            {
                "name": 'mail_protocol', "label": 'Protocol',
                "row": 11, "col": {"sm": 12, "md": 6},
                "type": "select", "autofocus": True
            },
            {
                "name": 'mail_mailpath', "label": 'Mail path',
                "row": 11, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_smtp_host', "label": 'SMTP host',
                "row": 12, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_smtp_port', "label": 'SMTP port',
                "row": 12, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_smtp_timeout', "label": 'SMTP timeout',
                "row": 13, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_smtp_keepalive', "label": 'SMTP keepalive',
                "row": 13, "col": {"sm": 12, "md": 6},
                "type": "select",
            },
            {
                "name": 'l2', "label": 'Validate', "icon": ft.Icons.CHECK,
                "row": 20, "col": {"sm": 12},
                "type": "heading"
            },
            {
                "name": 'mail_validate', "label": 'Validate', "row": 21,
                "col": {"sm": 12, "md": 6},
                "type": "select",
            },
            {
                "name": 'mail_smtp_user', "label": 'SMTP user',
                "row": 21, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_smtp_pass', "label": 'SMTP password',
                "row": 21, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_smtp_crypto', "label": 'SMTP crypto',
                "row": 22, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": 'l3', "label": 'Content', "icon": ft.Icons.TEXT_FIELDS,
                "row": 30, "col": {"sm": 12},
                "type": "heading"
            },
            {
                "name": 'mail_mailtype', "label": 'Mail type',
                "row": 31, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": 'mail_wordwrap', "label": 'Word Wrap',
                "row": 31, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": 'mail_wrapchars', "label": 'Wrap Chars',
                "row": 31, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_crlf', "label": 'CRLF',
                "row": 32, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": 'mail_newline', "label": 'Newline',
                "row": 32, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": 'mail_useragent', "label": 'User Agent',
                "row": 33, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'l4', "label": 'Header', "icon": ft.Icons.HEADPHONES,
                "row": 40, "col": {"sm": 12},
                "type": "heading"
            },
            {
                "name": 'mail_mime_version', "label": 'Header MIME-Version',
                "row": 41, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_content_type', "label": 'Header Content-Type',
                "row": 41, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'l5', "label": 'Address', "icon": ft.Icons.PERSON,
                "row": 50, "col": {"sm": 12},
                "type": "heading"
            },
            {
                "name": 'mail_from', "label": 'From',
                "row": 51, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_from_label', "label": 'From Label',
                "row": 51, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_reply_to', "label": 'Reply To',
                "row": 52, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'mail_reply_to_label', "label": 'Reply To Label',
                "row": 52, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'l9', "label": 'Test Mail', "icon": ft.Icons.MAIL,
                "row": 90, "col": {"sm": 12},
                "type": "heading"
            },
            {
                "name": 'to', "label": 'To',
                "row": 91, "col": {"sm": 12, "md": 6},
                "type": "input"
            },
            {
                "name": 'subject', "label": 'Subject',
                "row": 93, "col": {"sm": 12},
                "type": "input"
            },
            {
                "name": 'message', "label": 'Message',
                "row": 94, "col": {"sm": 12}, "multiline": True, "min_lines": 3, "max_lines": 50,
                "type": "input"},
            {
                "name": 'send', "label": 'Send', "icon": ft.Icons.MAIL,
                "row": 95, "col": {"sm": 12},
                "type": "button", "on_click": self.callback_send,
                "width": 150, "alignment": ft.Alignment.BOTTOM_RIGHT
            },
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="edit",
            fields=self.fields
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Mail Config")

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        self.form.submit()

    def callback_send(self, e):
        form_data = self.form.serialize()
        params = {
            "to": form_data.get("input_to"),
            "subject": form_data.get("input_subject"),
            "message": form_data.get("input_message")
        }
        endpoint = f"C_{self.module}/test_email"
        self.view.try_get(endpoint, params)
