import flet as ft

from components.modal.view import ModalView
from utils.http_client import HttpClient


class ModalPage:
    """Modal page class"""

    def __init__(self, page: ft.Page, modal: str, screen=str):
        """
        Initialize Modal Page

        Args:
            page: The Flet page
            modal: string
            screen: string
        """
        self.page = page
        self.modal = modal
        self.screen = screen
        self.title = "Change Shift"

        self.view = ModalView(page, modal, screen, title=self.title)

        self.shift_options = []
        self.selected_shift_id = None

        self.shift_dropdown = ft.Dropdown(
            label="Select Shift",
            hint_text="Choose a shift",
            leading_icon=ft.Icons.ACCESS_TIME,
            border_radius=10,
            width=300,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
            on_select=self.on_shift_change,
        )

        # Load shift options on init
        self.load_shift_options()

    def load_shift_options(self):
        """Load shift options from API"""
        client = HttpClient(self.page)
        response = client.get("C_home/call_shift_id_select")

        if isinstance(response, list):
            self.shift_options = response
            options = []
            for item in response:
                value = item.get("value", "")
                label = item.get("label", "")
                options.append(ft.dropdown.Option(key=str(value), text=label))
            self.shift_dropdown.options = options
        else:
            print(f"Error loading shift options: {response}")

    def on_shift_change(self, e):
        """Handle shift selection change"""
        self.selected_shift_id = e.control.value

    def build(self):
        """Build and return the modal screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text(
                        "Select your working shift",
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    padding=ft.Padding.only(bottom=10),
                ),
                self.shift_dropdown,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Button(
                    content="Submit",
                    width=300,
                    height=50,
                    on_click=self.on_click_submit,
                    icon=ft.Icons.SAVE,
                    bgcolor=ft.Colors.SECONDARY,
                    color=ft.Colors.ON_SECONDARY,
                    style=ft.ButtonStyle(
                        overlay_color=ft.Colors.TERTIARY
                    )
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            spacing=10,
        )

    def on_click_submit(self, e):
        self.view.dismiss_banner()

        if self.selected_shift_id is None or self.selected_shift_id == "":
            self.view.show_error("Please select a shift")
            return

        # Get storage and HTTP client
        storage = self.page.data.get("storage")
        if not storage:
            self.view.show_error("Session not found")
            return

        client = HttpClient(self.page)
        form_data = {
            "shift_id": self.selected_shift_id
        }
        response = client.post("C_home/call_change_shift", data=form_data)

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return
        elif isinstance(response, dict) and "success" in response:
            self.view.show_success(response.get("message", "Shift updated successfully"))
            self.page.update()
            return

        message = response[0] if isinstance(response, list) else response
        if isinstance(message, dict):
            if "success" in message:
                self.view.show_success(message.get("message", "Shift updated successfully"))
            elif "error" in message:
                self.view.show_error(message.get("error", "Unknown error"))
        elif isinstance(message, str):
            if "success" in message.lower():
                self.view.show_success(message)
            else:
                self.view.show_error(message)

        self.page.update()
