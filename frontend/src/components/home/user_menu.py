"""
User Menu component for displaying user configuration
"""

import flet as ft

from repository.storage import Storage


class UserMenu:
    """User Menu component"""

    def __init__(self, page: ft.Page):
        """
        Initialize user menu

        Args:
            page: The Flet page
        """
        self.page = page
        self.storage: Storage = page.data["storage"]
        self.icon_color = ft.Colors.ON_SURFACE

        if self.storage.client_data:
            self.username = self.storage.client_data.get_username()
        else:
            self.username = "User"
        self.menu_button = None

    def build(self):
        """Create the menu button"""
        # Get current theme mode for icon display
        current_theme = self.storage.theme_mode.get() if self.storage else "light"
        theme_icon = (
            ft.Icons.DARK_MODE if current_theme == "light" else ft.Icons.LIGHT_MODE
        )
        theme_text = "Dark Mode" if current_theme == "light" else "Light Mode"

        self.menu_button = ft.PopupMenuButton(
            icon=ft.Icons.SETTINGS,
            icon_color=self.icon_color,
            # Match the AppBar's other IconButtons (back/search) explicitly -
            # PopupMenuButton's own default icon size doesn't resolve to the
            # same size as IconButton's, so left implicit they render visibly
            # different next to each other in the top bar.
            icon_size=24,
            tooltip="Menu",
            menu_position=ft.PopupMenuPosition.UNDER,
            items=[
                ft.PopupMenuItem(icon=ft.Icons.PERSON, content=self.username),
                ft.PopupMenuItem(),  # Divider
                ft.PopupMenuItem(
                    icon=theme_icon,
                    content=theme_text,
                    on_click=self.on_toggle_theme_click,
                ),
                ft.PopupMenuItem(),  # Divider
                ft.PopupMenuItem(
                    icon=ft.Icons.SETTINGS_SYSTEM_DAYDREAM,
                    content="Change Shift",
                    on_click=self.on_change_shift_click,
                ),
                ft.PopupMenuItem(
                    icon=ft.Icons.KEY,
                    content="Change Token",
                    on_click=self.on_change_token_click,
                ),
                ft.PopupMenuItem(
                    icon=ft.Icons.LOCK,
                    content="Change Password",
                    on_click=self.on_change_password_click,
                ),
                ft.PopupMenuItem(
                    icon=ft.Icons.SECURITY,
                    content="Setup TOTP",
                    on_click=self.on_setup_totp_click,
                ),
                ft.PopupMenuItem(),  # Divider
                ft.PopupMenuItem(
                    icon=ft.Icons.BUILD,
                    content="Troubleshooting",
                    on_click=self.on_troubleshooting_click,
                ),
                ft.PopupMenuItem(),  # Divider
                ft.PopupMenuItem(
                    icon=ft.Icons.LOGOUT,
                    content="Logout",
                    on_click=self.on_logout_click,
                ),
            ],
        )
        return self.menu_button

    def on_change_shift_click(self, e):
        """Navigate to change shift page"""
        self.page.run_task(self.page.push_route, "/modals/shift/index")

    def on_change_token_click(self, e):
        """Navigate to change token page"""
        self.page.run_task(self.page.push_route, "/modals/token/index")

    def on_change_password_click(self, e):
        """Navigate to change password page"""
        self.page.run_task(self.page.push_route, "/modals/password/index")

    def on_setup_totp_click(self, e):
        """Navigate to TOTP setup page"""
        self.page.run_task(self.page.push_route, "/modals/totp/index")

    def on_toggle_theme_click(self, e):
        """Toggle between light and dark theme"""
        if self.storage:
            new_theme = self.storage.theme_mode.toggle()
            if self.menu_button:
                theme_icon = (
                    ft.Icons.DARK_MODE if new_theme == "light" else ft.Icons.LIGHT_MODE
                )
                theme_text = "Dark Mode" if new_theme == "light" else "Light Mode"
                self.menu_button.items[2] = ft.PopupMenuItem(
                    icon=theme_icon,
                    content=theme_text,
                    on_click=self.on_toggle_theme_click,
                )
                self.menu_button.update()
            self.page.update()

    def on_troubleshooting_click(self, e):
        """Navigate to troubleshooting page"""
        self.page.run_task(self.page.push_route, "/troubleshooting")

    def on_logout_click(self, e):
        """Logout user and redirect to login"""
        if self.storage:
            self.storage.clear()

        self.page.run_task(self.page.push_route, "/login")
