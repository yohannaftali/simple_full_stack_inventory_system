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
        self.title = "Change Token"

        self.view = ModalView(page, modal, screen, title=self.title)

        self.current_token = ft.TextField(
            label="Current Token",
            hint_text="Enter your current token",
            prefix_icon=ft.Icon(ft.Icons.TOKEN, color=ft.Colors.ON_SURFACE),
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

        self.new_token = ft.TextField(
            label="New Token",
            hint_text="Enter your new token",
            prefix_icon=ft.Icon(ft.Icons.TOKEN_OUTLINED, color=ft.Colors.ON_SURFACE),
            password=True,
            can_reveal_password=True,
            border_radius=10,
            border_color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            width=300,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
        )

        self.new_token_confirmation = ft.TextField(
            label="New Token Confirmation",
            hint_text="Enter your new token confirmation",
            prefix_icon=ft.Icon(ft.Icons.TOKEN_OUTLINED, color=ft.Colors.ON_SURFACE),
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
        return ft.Column(
            controls=[
                self.current_token,
                self.new_token,
                self.new_token_confirmation,
                ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
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
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def on_click_submit(self, e):
        self.view.dismiss_banner()

        print("Submit")
        current_token = self.current_token.value
        if current_token == "":
            print(current_token)
            self.view.show_error("Token is empty")
            return

        new_token = self.new_token.value
        if new_token == "":
            self.view.show_error("New token is empty")
            return

        new_token_confirmation = self.new_token_confirmation.value
        if new_token_confirmation == "":
            self.view.show_error("New token confirmation is empty")
            return

        if new_token != new_token_confirmation:
            self.view.show_error("New token not match")
            return

        if current_token == new_token:
            self.view.show_error("Current and new token are same")
            return

        # Get storage and HTTP client
        storage = self.page.data.get("storage")
        if not storage:
            self.view.show_error("Session not found")
            return

        client = HttpClient(self.page)
        form_data = {
            "ct": current_token,
            "nt": new_token,
            "ft": new_token_confirmation
        }
        response = client.post(
            "C_home/call_change_token",
            data=form_data,
            sensitive_keys={"ct", "nt", "ft"},
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
        self.current_token.value = ""
        self.new_token.value = ""
        self.new_token_confirmation.value = ""
        self.page.update()
