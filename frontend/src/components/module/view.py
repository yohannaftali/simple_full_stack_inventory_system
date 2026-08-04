"""
View component for the Module
"""

import flet as ft

from components.module.footer import ModuleFooter
from components.module.header import ModuleHeader
from components.module.toolbar import ModuleToolbar
from utils.http_client import HttpClient


class ModuleView:
    """Body component"""

    def __init__(
        self,
        page: ft.Page,
        module: str,
        screen=str,
        title: str = None,
        footer_controls=None,
    ):
        """
        Initialize body

        Args:
            page: The Flet page
            module: string
            screen: string
            label: string
        """
        self.page = page
        self.module = module
        self.screen = screen

        storage = page.data.get("storage")
        module_label = module  # default fallback

        if storage and storage.client_data:
            module_object = storage.client_data.get_module_by_name(module)
            if module_object:
                module_label = module_object.get("label", module)

        self.label = module_label

        # The module name (subtitle line, issue #83) is set once here, at
        # construction - individual screens only ever call
        # `self.view.header.set_title(...)` afterward to set their own
        # page-specific headline, never the module name itself. An index
        # screen never calls set_title() at all, so its AppBar correctly
        # falls back to the module name alone (see
        # ModuleHeader._build_title_control()) instead of a redundant
        # "Module / Module" two-line block the old `f"{module_label} -
        # {screen}"` fallback would have produced.
        self.header = ModuleHeader(page, module_label=module_label)
        if title is not None:
            self.header.set_title(title)
        self.controls = None
        self.footer = ModuleFooter(page, controls=footer_controls)
        self.toolbar = ModuleToolbar(page)
        if not hasattr(page, "banner"):
            page.banner = None

    def build(self, body, padding: int = 0, bgcolor=ft.Colors.SURFACE):
        """Build and return the module screen page UI"""
        if self.controls is not None:
            controls = self.controls
        else:
            controls = []
            # An empty ModuleToolbar (no buttons added) still builds a real
            # ft.Container() and used to be added here unconditionally - even
            # a childless Container occupies a Column slot, so skip it
            # entirely instead of relying on its size resolving to zero.
            has_toolbar = self.toolbar.left is not None or self.toolbar.right is not None
            if has_toolbar:
                controls.append(self.toolbar.build())
            controls.append(ft.Container(content=body, expand=True))
            controls.append(self.footer.build())

        # Desktop windows have no notch/status bar to dodge, but SafeArea's
        # avoid_intrusions_top still reserved top padding here, showing as a
        # thin white strip between the AppBar and the toolbar/search bar on
        # every module screen. Keep the intrusion-avoidance on Android/iOS,
        # where it's actually needed for the notch/status bar.
        is_desktop = not self.page.web and self.page.platform in (
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.MACOS,
            ft.PagePlatform.LINUX,
        )

        return ft.View(
            route=f"/modules/{self.module}/{self.screen}",
            controls=[
                self.header.build(),
                ft.SafeArea(
                    content=ft.Container(
                        content=ft.Column(
                            controls,
                            spacing=0,
                            expand=True,
                        ),
                        alignment=ft.Alignment.CENTER,
                        padding=padding,
                        expand=True,
                    ),
                    avoid_intrusions_top=not is_desktop,
                    expand=True,
                ),
            ],
            spacing=0,
            padding=0,
            bgcolor=bgcolor,
        )

    def unsafe_build(self, body, padding: int = 0, bgcolor=ft.Colors.SURFACE):
        """Build and return the module screen page UI"""
        return ft.View(
            route=f"/modules/{self.module}/{self.screen}",
            controls=[
                self.header.build(),
                body,
            ],
            padding=padding,
            bgcolor=bgcolor,
        )

    def show_error(self, message):
        """Show error banner"""
        self.dismiss_banner()

        # Flet 0.85 removed Page.banner / Page.open() as built-ins. We keep
        # `page.banner` as a plain attribute (other components dismiss it via
        # `self.page.banner.open = False`) but show it by appending to
        # page.overlay and setting `open = True`.
        self.page.banner = ft.Banner(
            bgcolor=ft.Colors.ERROR_CONTAINER,
            leading=ft.Icon(
                ft.Icons.WARNING_AMBER_ROUNDED,
                color=ft.Colors.ON_ERROR_CONTAINER,
                size=40,
            ),
            content=ft.Text(
                message,
                color=ft.Colors.ON_ERROR_CONTAINER,
            ),
            actions=[
                ft.TextButton(
                    content="Close",
                    style=ft.ButtonStyle(color=ft.Colors.ON_ERROR_CONTAINER),
                    on_click=self.dismiss_banner,
                )
            ],
        )
        self.page.overlay.append(self.page.banner)
        self.page.banner.open = True
        self.page.update()

    def dismiss_banner(self, e=None):
        if hasattr(self.page, "banner") and self.page.banner:
            self.page.banner.open = False
            self.page.update()

    def show_success(self, message):
        """Show success banner"""
        self.dismiss_banner()

        self.page.banner = ft.Banner(
            bgcolor=ft.Colors.SURFACE,
            leading=ft.Icon(
                ft.Icons.CHECK_CIRCLE,
                color=ft.Colors.ON_SURFACE,
                size=40,
            ),
            content=ft.Text(
                message,
                color=ft.Colors.ON_SURFACE,
            ),
            actions=[
                ft.TextButton(
                    content="Close",
                    style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE),
                    on_click=self.dismiss_banner,
                )
            ],
        )
        self.page.overlay.append(self.page.banner)
        self.page.banner.open = True
        self.page.update()

    def get_response(self, endpoint: str, params: dict | None = None):
        client = HttpClient(self.page)
        response = client.get(endpoint, params=params)
        return response

    def handle_response(self, response, callback_success=None, callback_error=None):
        if isinstance(response, dict) and "error" in response:
            self.show_error(response["error"])
            if callback_error is not None:
                callback_error(response)
            return

        message_text = self.extract_message(response)
        if "error" in message_text:
            self.show_error(message_text)
            if callback_error is not None:
                callback_error(response)
        else:
            self.show_success(message_text or "Form submitted successfully.")
            if callback_success is not None:
                callback_success(response)

    def extract_message(self, obj) -> str:
        # Try common keys used by the API, fall back to string representation
        if isinstance(obj, dict):
            for key in ("msg", "message", "error", "status"):
                if key in obj and obj[key] is not None:
                    return str(obj[key])
            return str(obj)
        if isinstance(obj, list):
            if len(obj) == 0:
                return ""
            return self.extract_message(obj[0])
        return str(obj)

    def try_get(
        self,
        endpoint: str,
        params: dict | None = None,
        callback_success=None,
        callback_error=None,
    ):
        response = self.get_response(endpoint=endpoint, params=params)
        self.handle_response(
            response=response,
            callback_success=callback_success,
            callback_error=callback_error,
        )
