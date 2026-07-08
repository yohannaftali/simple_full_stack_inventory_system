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
                "name": "inspection_header_id",
                "type": "hidden", "key": True
            },
            {
                "name": "model_id", "label": "Model", "icon": ft.Icons.DIRECTIONS_CAR,
                "row": 10, "col": {"sm": 12},
                "type": "select"
            },
            {
                "name": "line_id", "label": "Line", "icon": ft.Icons.ADD_ROAD,
                "row": 20, "col": {"sm": 12},
                "type": "select"
            },
            {
                "name": "vin_no", "label": "Chassis No", "icon": ft.Icons.NUMBERS,
                "row": 30, "col": {"sm": 12},
                "type": "input"
            },
            {
                "name": "engine_no", "label": "Engine No", "icon": ft.Icons.SETTINGS,
                "row": 40, "col": {"sm": 12},
                "type": "input"
            },
            {
                "name": "color_id", "label": "Color", "icon": ft.Icons.COLOR_LENS,
                "row": 50, "col": {"sm": 12},
                "type": "select"
            },
            {
                "name": "country_id", "label": "Country", "icon": ft.Icons.FLAG,
                "row": 60, "col": {"sm": 12},
                "type": "select",
                "depends_on": "model_id"
            },
            {
                "name": "cu_username", "label": "PIC", "icon": ft.Icons.PERSON,
                "row": 70, "col": {"sm": 12},
                "type": "select"
            },
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="edit",
            fields=self.fields
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Receiving")
        
        # Override back button to navigate back to detail with record_id
        self.view.header.on_click = self.on_back_click

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def on_back_click(self, e):
        """Navigate back to detail page with record_id preserved"""
        if hasattr(self.page, 'banner') and self.page.banner:
            self.page.banner.open = False
            self.page.update()
        
        if self.record_id:
            # Go back to detail page with the record_id
            self.page.run_task(self.page.push_route, f"/modules/{self.module}/detail/{self.record_id}")
        else:
            # Fallback to index if no record_id
            self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return self.form.build()

    def callback_submit(self, e):
        """Custom submit that redirects to detail page instead of index based on framework"""
        form_data = self.form.serialize(self.fields)
        client = HttpClient(self.page)
        response = client.post(self.form.endpoint_submit, data=form_data)

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response['error'])
            return

        # Extract message from response
        message_text = self.form.extract_message(response)
        if "error" in message_text.lower():
            self.view.show_error(message_text)
        else:
            self.view.show_success(message_text or "Form submitted successfully.")
            # Reset input fields after successful submit
            self.form.reset()
            # Redirect to detail page with record_id instead of index
            if self.record_id:
                self.page.run_task(self.page.push_route, f"/modules/{self.module}/detail/{self.record_id}")
            else:
                self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")
