import base64
import io
import threading
import time

import flet as ft
import qrcode
import qrcode.image.pure

from components.modal.view import ModalView
from utils.http_client import HttpClient


class ModalPage:
    """TOTP Setup modal page"""

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
        self.title = "Setup TOTP"
        self._secret = ""
        self._clipboard: ft.Clipboard | None = None

        self.view = ModalView(page, modal, screen, title=self.title)

        self.qr_image = ft.Image(
            width=160,
            height=160,
            visible=False,
            fit=ft.BoxFit.CONTAIN,
            src="",
        )

        self.secret_field = ft.TextField(
            label="Secret Key",
            read_only=True,
            visible=False,
            border_radius=10,
            border_color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            width=300,
            text_size=14,
            color=ft.Colors.ON_SURFACE,
            suffix=ft.IconButton(
                icon=ft.Icons.COPY,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                tooltip="Copy secret",
                on_click=self.on_copy_secret_click,
            ),
        )

        self.verify_input = ft.TextField(
            label="Verification Code",
            hint_text="Enter 6-digit code from authenticator",
            prefix_icon=ft.Icon(ft.Icons.VERIFIED_USER, color=ft.Colors.ON_SURFACE),
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=6,
            input_filter=ft.NumbersOnlyInputFilter(),
            border_radius=10,
            border_color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY_CONTAINER),
            visible=False,
            width=300,
            text_size=16,
            color=ft.Colors.ON_SURFACE,
        )

        self.generate_button = ft.Button(
            content="Generate",
            icon=ft.Icons.REFRESH,
            width=300,
            height=50,
            on_click=self.on_generate_click,
            bgcolor=ft.Colors.SECONDARY,
            color=ft.Colors.ON_SECONDARY,
            style=ft.ButtonStyle(overlay_color=ft.Colors.TERTIARY),
        )

        self.save_button = ft.Button(
            content="Save",
            icon=ft.Icons.SAVE,
            width=300,
            height=50,
            on_click=self.on_save_click,
            visible=False,
            bgcolor=ft.Colors.PRIMARY,
            color=ft.Colors.ON_PRIMARY,
            style=ft.ButtonStyle(overlay_color=ft.Colors.TERTIARY),
        )

    def build(self):
        """Build and return the modal screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return ft.Column(
            controls=[
                ft.Text(
                    "Scan QR with your authenticator app, then enter the 6-digit code to save.",
                    text_align=ft.TextAlign.CENTER,
                    size=13,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    width=300,
                ),
                ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                self.qr_image,
                self.secret_field,
                self.verify_input,
                ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                self.generate_button,
                self.save_button,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def on_generate_click(self, e):
        self.view.dismiss_banner()
        self.generate_button.text = "Generating..."
        self.generate_button.disabled = True
        self.page.update()

        def _do_generate():
            try:
                client = HttpClient(self.page)
                response = client.get("C_home/call_generate_totp")

                if isinstance(response, dict) and "error" in response:
                    self.generate_button.text = "Generate"
                    self.generate_button.disabled = False
                    self.view.show_error(response["error"])
                    self.page.update()
                    return

                if not isinstance(response, dict) or "secret" not in response:
                    self.generate_button.text = "Generate"
                    self.generate_button.disabled = False
                    self.view.show_error("Failed to generate TOTP. Please try again.")
                    self.page.update()
                    return

                self._secret = response["secret"]

                # Build TOTP URI and generate QR as PNG in Python
                storage = self.page.data.get("storage")
                username = storage.client_data.get_username() if storage else "user"
                totp_uri = (
                    f"otpauth://totp/SFSIS%3A{username}"
                    f"?secret={self._secret}&issuer=SFSIS"
                    f"&algorithm=SHA1&digits=6&period=30"
                )

                qr = qrcode.QRCode(box_size=4, border=2)
                qr.add_data(totp_uri)
                qr.make(fit=True)
                img = qr.make_image(image_factory=qrcode.image.pure.PyPNGImage)
                buf = io.BytesIO()
                img.save(buf)
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                self.qr_image.src = qr_b64
                self.qr_image.visible = True
                self.secret_field.value = self._secret
                self.secret_field.visible = True
                self.verify_input.value = ""
                self.verify_input.visible = True
                self.save_button.visible = True
                self.generate_button.visible = False

                self.page.update()

            except Exception as ex:
                print(f"TOTP generate error: {ex}")
                self.generate_button.text = "Generate"
                self.generate_button.disabled = False
                self.view.show_error(f"Error: {ex}")
                self.page.update()

        threading.Thread(target=_do_generate, daemon=True).start()

    async def on_copy_secret_click(self, e):
        # `page.set_clipboard(...)` doesn't exist in Flet 0.85 - clipboard
        # access is `ft.Clipboard`, a `Service` (not a plain page method),
        # same "lazy page.services registration inside an async handler"
        # pattern components/table/menu.py already established for
        # FilePicker: `page.services` resolves through the root view and
        # raises RuntimeError while `page.views` is empty (true during
        # __init__), and only an `async def` handler gets awaited by
        # Flet's dispatcher, so both the registration and the `set()` call
        # have to happen here, not in the constructor or a sync handler.
        if not self._secret:
            return
        if self._clipboard is None:
            self._clipboard = ft.Clipboard()
        if self._clipboard not in self.page.services:
            self.page.services.append(self._clipboard)
            self.page.update()
        await self._clipboard.set(self._secret)
        self.view.show_success("Secret copied to clipboard")

    def on_save_click(self, e):
        self.view.dismiss_banner()

        totp_value = self.verify_input.value or ""
        if len(totp_value) != 6 or not totp_value.isdigit():
            self.view.show_error("Please enter a valid 6-digit verification code")
            return

        if not self._secret:
            self.view.show_error("No secret generated. Please generate first.")
            return

        self.save_button.text = "Saving..."
        self.save_button.disabled = True
        self.page.update()

        secret = self._secret

        def _do_save():
            client = HttpClient(self.page)
            form_data = {
                "secret": secret,
                "totp": totp_value,
            }
            response = client.post("C_home/call_change_totp", data=form_data)

            self.save_button.text = "Save"
            self.save_button.disabled = False

            if isinstance(response, dict) and "error" in response:
                self.view.show_error(response["error"])
                self.page.update()
                return

            if isinstance(response, dict) and "success" in response:
                self.view.show_success(response["success"])
                self._reset_form()
                self.page.update()
                self._go_home_after_delay()
                return

            message = response[0] if isinstance(response, list) else str(response)
            if "success" in message.lower():
                self.view.show_success(message)
                self._reset_form()
                self.page.update()
                self._go_home_after_delay()
            else:
                self.view.show_error(message)
                self.page.update()

        threading.Thread(target=_do_save, daemon=True).start()

    def _reset_form(self):
        self._secret = ""
        self.qr_image.src = ""
        self.qr_image.visible = False
        self.secret_field.value = ""
        self.secret_field.visible = False
        self.verify_input.value = ""
        self.verify_input.visible = False
        self.save_button.visible = False
        self.generate_button.text = "Generate"
        self.generate_button.disabled = False
        self.generate_button.visible = True

    def _go_home_after_delay(self):
        def _navigate():
            time.sleep(1.5)
            self.page.run_task(self.page.push_route, "/home")
            self.page.update()

        threading.Thread(target=_navigate, daemon=True).start()
