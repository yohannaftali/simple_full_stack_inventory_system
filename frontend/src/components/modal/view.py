"""
View component for the Modal
"""
import flet as ft

from components.modal.header import ModalHeader


class ModalView:
    """Body component"""

    def __init__(self, page: ft.Page, modal: str, screen=str, title: str = None):
        """
        Initialize body

        Args:
            page: The Flet page
            modal: string
            screen: string
            label: string
        """
        self.page = page
        self.modal = modal
        self.screen = screen
        self.title = title if title is not None else f"{modal} - {screen}" if screen != "index" else modal

        self.header = ModalHeader(page)
        self.header.set_title(self.title)
        if not hasattr(page, "banner"):
            page.banner = None

    def build(self, body, padding: int = 24, bgcolor=ft.Colors.SURFACE, show_divider: bool = False):
        """Build and return the module screen page UI

        `padding=24` (was 20) and the 560dp max-width wrapper below match
        the M3 full-screen dialog spec's own container measurements
        (issue #85) - "Top/left/right padding: 24dp",
        "Container width; Max 560dp". `show_divider` is the spec's own
        optional 1dp divider under the header, off by default.
        """
        controls = [self.header.build()]
        if show_divider:
            controls.append(ft.Divider(height=1, thickness=1, color=ft.Colors.OUTLINE_VARIANT))
        # A fixed `width=560` would force horizontal overflow on any
        # narrower (mobile) viewport - Flet's Container has no dedicated
        # "max-width" property, so cap against the page's own live width
        # instead: full width below 560, capped and centered above it.
        page_width = getattr(self.page, "width", None) or 0
        body_width = min(page_width, 560) if page_width else None
        controls.append(
            ft.SafeArea(
                content=ft.Container(
                    content=ft.Container(
                        content=body,
                        padding=padding,
                        expand=True,
                        width=body_width,
                    ),
                    alignment=ft.Alignment.TOP_CENTER,
                    expand=True,
                ),
                expand=True,
            ),
        )
        return ft.View(
            route=f"/modals/{self.modal}/{self.screen}",
            controls=controls,
            spacing=0,
            padding=0,
            bgcolor=bgcolor,
        )

    def unsafe_build(self, body, padding: int = 0, bgcolor=ft.Colors.SURFACE):
        """Build and return the modal screen page UI"""
        return ft.View(
            route=f"/modals/{self.modal}/{self.screen}",
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
        if hasattr(self.page, 'banner') and self.page.banner:
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
