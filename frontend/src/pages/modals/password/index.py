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
            module: string
            screen: string
        """
        self.page = page
        self.modal = modal
        self.screen = screen
        self.title = "Change Password"

        self.view = ModalView(page, modal, screen, title=self.title)
        self.view.header.set_action("Submit", self.on_click_submit)

        self.current_password = ft.TextField(
            label="Current Password",
            hint_text="Enter your current password",
            prefix_icon=ft.Icon(ft.Icons.LOCK, color=ft.Colors.ON_SURFACE),
            password=True,
            can_reveal_password=True,
            border_radius=10,
            border_color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            autofocus=True,
            width=300,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
        )

        self.new_password = ft.TextField(
            label="New Password",
            hint_text="Enter your new password",
            prefix_icon=ft.Icon(ft.Icons.LOCK_OUTLINED, color=ft.Colors.ON_SURFACE),
            password=True,
            can_reveal_password=True,
            border_radius=10,
            border_color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            width=300,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
        )

        self.new_password_confirmation = ft.TextField(
            label="New Password Confirmation",
            hint_text="Enter your new password confirmation",
            prefix_icon=ft.Icon(ft.Icons.LOCK_OUTLINED, color=ft.Colors.ON_SURFACE),
            password=True,
            can_reveal_password=True,
            border_radius=10,
            border_color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            width=300,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
        )

    def build(self):
        """Build and return the modal screen page UI"""
        return self.view.build(self.body())

    def body(self):
        # Submit lives in the header's own text button now (issue #85 -
        # M3 full-screen dialog convention), not a body-level button.
        return ft.Column(
            controls=[
                self.current_password,
                self.new_password,
                self.new_password_confirmation,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def on_click_submit(self, e):
        self.view.dismiss_banner()

        print("Submit")
        current_password = self.current_password.value
        if current_password == "":
            print(current_password)
            self.view.show_error("Password is empty")
            return

        new_password = self.new_password.value
        if new_password == "":
            self.view.show_error("New password is empty")
            return

        new_password_confirmation = self.new_password_confirmation.value
        if new_password_confirmation == "":
            self.view.show_error("New password confirmation is empty")
            return

        if new_password != new_password_confirmation:
            self.view.show_error("New password not match")
            return

        if current_password == new_password:
            self.view.show_error("Current and new password are same")
            return

        # Get storage and HTTP client
        storage = self.page.data.get("storage")
        if not storage:
            self.view.show_error("Session not found")
            return

        client = HttpClient(self.page)
        form_data = {
            "c": current_password,
            "n": new_password,
            "f": new_password_confirmation
        }
        response = client.post(
            "C_home/call_change_password",
            data=form_data,
            sensitive_keys={"c", "n", "f"},
        )

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return
        elif isinstance(response, dict) and "success" in response:
            self.view.show_error(response["success"])
            self.reset_form()
            return

        message = response[0] if isinstance(response, list) else response
        if "success" in message.lower():
            self.view.show_success(message)
            self.reset_form()
            self.page.update()
        else:
            self.view.show_error(message)

        return

    def reset_form(self):
        self.current_password.value = ""
        self.new_password.value = ""
        self.new_password_confirmation.value = ""
        self.page.update()
