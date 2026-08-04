"""
Header component for the modal
"""

import flet as ft

from components.module.header import (
    DIALOG_CLOSE_ICON_SIZE,
    DIALOG_HEADER_HEIGHT,
    DIALOG_HEADER_PADDING,
)


class ModalHeader:
    """M3 Full-screen dialog header (issue #85) - modals
    (password/totp/shift/token) are M3 Full-screen dialogs
    (https://m3.material.io/components/dialogs/overview), not module
    drill-down screens, so this is deliberately NOT `ModuleHeader`'s Small
    top app bar shape (back arrow + trailing icon action, issue #83) - a
    full-screen dialog's header is a close (X) affordance, an optional
    headline, and the primary action as a trailing TEXT button, per
    https://m3.material.io/components/dialogs/specs."""

    def __init__(self, page: ft.Page, screen_label: str = "Modal"):
        """
        Initialize header

        Args:
            page: The Flet page
            screen_label: str
        """
        self.page = page
        self.title = screen_label
        self._action_label: str | None = None
        self._action_on_click = None

    def set_action(self, label: str, on_click) -> None:
        """Register the dialog's primary action (e.g. "Save"/"Submit") as
        the header's trailing text button - the M3 full-screen dialog's
        own "Text button" element, replacing a body-level submit button.
        A screen with no natural single primary action (e.g. totp's
        two-step Generate-then-Save flow) simply never calls this, and
        the header renders with no trailing action at all."""
        self._action_label = label
        self._action_on_click = on_click

    def build(self):
        """Build and return the AppBar"""
        actions = []
        if self._action_label is not None:
            actions.append(
                ft.TextButton(
                    content=ft.Text(self._action_label, color=ft.Colors.PRIMARY),
                    on_click=self._action_on_click,
                )
            )

        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_color=ft.Colors.ON_SURFACE,
                icon_size=DIALOG_CLOSE_ICON_SIZE,
                width=DIALOG_CLOSE_ICON_SIZE + DIALOG_HEADER_PADDING * 2,
                height=DIALOG_HEADER_HEIGHT,
                tooltip="Close",
                on_click=self.on_click,
            ),
            leading_width=DIALOG_CLOSE_ICON_SIZE + DIALOG_HEADER_PADDING * 2,
            title=ft.Text(
                self.title,
                color=ft.Colors.ON_SURFACE,
                size=16,
                weight=ft.FontWeight.W_500,
            ),
            title_spacing=DIALOG_HEADER_PADDING,
            center_title=False,
            toolbar_height=DIALOG_HEADER_HEIGHT,
            # M3 full-screen dialog color mapping (issue #85) -
            # surfaceContainerHigh, distinct from the Small top app bar's
            # plain SURFACE (components/module/header.py).
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            actions=actions,
            actions_padding=ft.Padding.only(right=DIALOG_HEADER_PADDING),
            elevation=0,
            elevation_on_scroll=0,
            shadow_color=ft.Colors.SHADOW,
        )

    def set_title(self, title: str):
        """Set the title of the AppBar"""
        self.title = title

    def on_click(self, e):
        """Navigate back within module screens or to home if history exhausted."""
        # Close any open banners
        if hasattr(self.page, 'banner') and self.page.banner:
            self.page.banner.open = False
            self.page.update()

        history = []
        if hasattr(self.page, "data") and isinstance(self.page.data, dict):
            history = self.page.data.get("module_history", [])
        if history:
            prev_module, prev_screen, prev_record_id = history[-1]
            self.page.data["module_history"] = history
            route = f"/modules/{prev_module}/{prev_screen}"
            if prev_record_id is not None:
                route += f"/{prev_record_id}"
            self.page.run_task(self.page.push_route, route)
        else:
            self.page.run_task(self.page.push_route, "/home")
