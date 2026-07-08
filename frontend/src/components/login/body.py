"""
Body component for the login
"""

import flet as ft

from repository.storage import Storage
from utils.http_client import HttpClient

from components.login.login_button import LoginButton
from components.login.troubleshooting_button import TroubleshootingButton


class Body:
    """Body component"""

    def __init__(self, page: ft.Page):
        """
            Initialize body

            Args:
                page: The Flet page
            """
        self.page = page
        self.storage: Storage = page.data["storage"]

        # Error message text
        self.error_text = ft.Text(
            "",
            color=ft.Colors.ERROR,
            size=14,
            visible=False,
        )

        # Username field
        self.username_field = ft.TextField(
            label="Username",
            hint_text="Enter your username",
            prefix_icon=ft.Icons.PERSON,
            border_radius=10,
            autofocus=True,
            width=300,
            on_blur=self.on_username_blur,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
        )

        # Password field
        self.password_field = ft.TextField(
            label="Password",
            hint_text="Enter your password",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            border_radius=10,
            width=300,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
        )

        # TOTP (authenticator) field
        self.totp_field = ft.TextField(
            label="Authenticator",
            hint_text="000000",
            prefix_icon=ft.Icons.SHIELD,
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=6,
            border_radius=10,
            width=300,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
        )

        # Login button
        self.login_button = LoginButton(on_click_callback=self.on_login_click)

        # Troubleshooting button (clear shared preferences, view logs)
        self.troubleshooting_button = TroubleshootingButton(
            on_click_callback=self.on_troubleshooting_click)

    def build(self):
        """Build and return the body column"""
        server_url = self.storage.server_url.get()
        if server_url is None:
            server_url = "Please select server"

        server_info = ft.Container(
            content=ft.Text(
                server_url,
                size=16,
                color=ft.Colors.TERTIARY,
                style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
            ),
            on_click=self.on_config_click,
            tooltip="Server Configuration",
        )

        controls = [
            ft.Icon(
                icon=ft.Icons.ACCOUNT_CIRCLE,
                size=40,
                color=ft.Colors.SECONDARY,
            ),
            ft.Text(
                "Login",
                size=32,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.PRIMARY,
            ),
            server_info,
            ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
            self.error_text,
            self.username_field,
            self.password_field,
            self.totp_field,
            ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
            self.login_button.build(),
            self.troubleshooting_button.build(),
        ]
        return ft.SafeArea(
            content=ft.Container(
                content=ft.Column(
                    controls=controls,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=20,
            ),
            expand=True,
        )

    def on_username_blur(self, e):
        """Handle username field blur - request token from server"""
        username = self.username_field.value
        if not username:
            return

        client = HttpClient(self.page)
        params = {"param": username}
        response = client.get("C_login/get_session", params)
        print(response)
        if response is None or not isinstance(response, dict):
            self.error_text.value = "Failed to connect to server"
            self.error_text.visible = True
            self.page.update()
        elif "error" in response:
            self.error_text.value = f"Connection error: {response['error']}"
            self.error_text.visible = True
            self.page.update()
        elif "tok" in response:
            # Store token in storage
            self.storage.set("_tok", response["tok"])
            self.error_text.visible = False
            self.page.update()
        else:
            self.error_text.value = "Failed to get token"
            self.error_text.visible = True
            self.page.update()

    def on_login_click(self, e):
        """Handle login button click"""
        username_value = self.username_field.value
        password_value = self.password_field.value
        totp_value = self.totp_field.value

        if not username_value or not password_value:
            self.error_text.value = "Please enter both username and password"
            self.error_text.visible = True
            self.page.update()
            return

        if not totp_value or not totp_value.strip():
            self.error_text.value = "Authenticator code is required"
            self.error_text.visible = True
            self.page.update()
            return

        # Refresh token right before submit — avoids 2-minute expiry window
        client = HttpClient(self.page)
        refresh = client.get("C_login/get_session", {"param": username_value})
        if not refresh or "tok" not in refresh:
            self.error_text.value = "Failed to get token. Check connection."
            self.error_text.visible = True
            self.page.update()
            return
        token = refresh["tok"]

        response = client.post("C_login/login", data={
            "username": username_value,
            "password": password_value,
            "totp": totp_value.strip(),
            "_tok": token,
            "client_type": "flet",
        })

        # Store cookies after login attempt
        cookies = client.get_cookies()
        if cookies is not None:
            self.storage.http_cookies.set(cookies)
            print(f"Set cookies: {cookies}")

        # Handle login response based on status code
        if response is None:
            self.error_text.value = "Failed to connect to server"
            self.error_text.visible = True
            self.page.update()
        elif isinstance(response, dict) and "status_code" in response:
            # Handle status code responses
            status_code = response["status_code"]
            if status_code == 200:
                # Login successful
                print("Login successful (200)")
                self.error_text.visible = False
                self.storage.user_session.set(username_value, token)
                self.storage.client_data.refresh()
                self.page.run_task(self.page.push_route, "/home")
            elif status_code == 304:
                # Already authenticated
                print("Already authenticated (304)")
                self.error_text.visible = False
                self.storage.user_session.set(username_value, token)
                self.page.run_task(self.page.push_route, "/home")
            elif status_code == 403 or status_code == 401:
                # Unauthorized
                print(f"Login failed ({status_code} Unauthorized)")
                self.error_text.value = "Invalid credentials"
                self.error_text.visible = True
                self.page.update()
            else:
                self.error_text.value = f"Unexpected status: {status_code}"
                self.error_text.visible = True
                self.page.update()
        elif isinstance(response, dict) and "error" in response:
            # Handle error responses with status codes
            if response.get("status_code") in [403, 401]:
                self.error_text.value = "Invalid credentials"
            else:
                self.error_text.value = f"Connection error: {response['error']}"
            self.error_text.visible = True
            self.page.update()

    def on_config_click(self, e):
        """Navigate to config page"""
        self.page.run_task(self.page.push_route, "/server_config")

    def on_troubleshooting_click(self, e):
        """Navigate to troubleshooting page"""
        self.page.run_task(self.page.push_route, "/troubleshooting")
