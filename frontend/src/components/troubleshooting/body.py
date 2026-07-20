"""
Body component for the troubleshooting page
"""

import asyncio

import flet as ft

from components.splash_screen import SplashScreen
from repository.storage import Storage
from utils.app_logger import get_log_file_path, get_recent_logs
from utils.module_loader import ModuleLoader
from utils.storage_compat import sp_call_with_retry


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

        self.log_text = ft.Text(
            "",
            size=11,
            font_family="monospace",
            selectable=True,
            no_wrap=False,
        )
        self.log_view = ft.Container(
            content=ft.Column(
                controls=[self.log_text],
                scroll=ft.ScrollMode.ALWAYS,
            ),
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
            border_radius=8,
            padding=10,
            height=300,
            visible=False,
        )

    def build(self):
        """Build and return the body column"""
        # Web has no Server Configuration screen and never persists a
        # server URL at all (issue #36 - it's always the fixed
        # FRONTEND_DEFAULT_SERVER_URL), so a hard reset there has nothing
        # to say about it.
        is_web = bool(getattr(self.page, "web", False))
        hard_reset_description = (
            "Hard reset removes the saved login session and theme on this "
            "device. Use this if the app is stuck in a bad state."
            if is_web
            else
            "Hard reset removes the saved "
            "server URL, login session, and theme on this "
            "device. Use this if the app is stuck in a bad "
            "state."
        )
        return ft.SafeArea(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Diagnostics and hard-reset tools for this device.",
                            size=13,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Button(
                            content="Show Logs",
                            icon=ft.Icons.ARTICLE,
                            width=300,
                            height=50,
                            on_click=self.on_show_logs_click,
                            bgcolor=ft.Colors.SECONDARY,
                            color=ft.Colors.ON_SECONDARY,
                        ),
                        self.log_view,
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        ft.Text(
                            hard_reset_description,
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Button(
                            content="Hard Reset",
                            icon=ft.Icons.RESTART_ALT,
                            width=300,
                            height=50,
                            on_click=self.on_hard_reset_click,
                            bgcolor=ft.Colors.ERROR,
                            color=ft.Colors.ON_ERROR,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
                expand=True,
            ),
            expand=True,
        )

    def on_show_logs_click(self, e):
        """Toggle the log view and refresh its content"""
        log_path = get_log_file_path()
        header = (
            f"Log file: {log_path}\n\n" if log_path else "Log file: (not available)\n\n"
        )
        self.log_text.value = header + get_recent_logs()
        self.log_view.visible = True
        self.page.update()

    def on_hard_reset_click(self, e):
        """Show a confirmation dialog before wiping shared preferences"""
        is_web = bool(getattr(self.page, "web", False))
        dialog_text = (
            "This removes the saved login session and theme on this "
            "device, and returns you to the Login screen, like a fresh "
            "install. This cannot be undone."
            if is_web
            else
            "This removes the saved server URL, login session, and "
            "theme on this device, and returns you to the Server "
            "Configuration screen, like a fresh install. This cannot "
            "be undone."
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Hard Reset?"),
            content=ft.Text(dialog_text),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_dialog()),
                ft.Button(
                    "Clear",
                    on_click=self._confirm_hard_reset,
                    bgcolor=ft.Colors.ERROR,
                    color=ft.Colors.ON_ERROR,
                ),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _confirm_hard_reset(self, e):
        self._close_dialog()
        self.page.run_task(self._do_hard_reset)

    def _close_dialog(self):
        for control in self.page.overlay:
            if isinstance(control, ft.AlertDialog):
                control.open = False
        self.page.update()

    async def _do_hard_reset(self):
        # Mirror the app's startup look: show the splash screen while the
        # reset runs, then land on Server Configuration - after a hard
        # reset, server_url falls back to DEFAULT_SERVER_URL just like a
        # brand new install, so this is the same "not configured yet"
        # destination main.py sends first-time users to. Web has no
        # Server Configuration screen at all (issue #36 - ServerURL never
        # persists there), so it goes to /login instead - the same
        # destination _boot_navigate itself would choose on web with no
        # active session.
        is_web = bool(getattr(self.page, "web", False))
        splash = SplashScreen(self.page)
        self.page.views.clear()
        self.page.views.append(splash.build())
        self.page.update()
        await asyncio.sleep(0.05)

        splash.set_progress(None, "Hard reset...")
        await self.storage.clear_all_persistent()

        # Also drop every preloaded module/modal and re-import fresh
        # (not from cache) - a hard reset is meant to be a full "like new"
        # recovery, so it shouldn't leave stale code from before the reset
        # sitting in memory either.
        ModuleLoader.reset_cache()
        modules = ModuleLoader(page=self.page, target="modules")
        modals = ModuleLoader(page=self.page, target="modals")

        def _report_progress(loaded: int, total: int, item: str, screen: str):
            fraction = loaded / total if total else 1.0
            splash.set_progress(fraction, f"Loading {item}/{screen}...")

        splash.set_progress(0, "Loading modules...")
        modules.preload(on_progress=_report_progress)
        splash.set_progress(0, "Loading modals...")
        modals.preload(on_progress=_report_progress)
        splash.set_progress(1, "Done")

        target_route = "/login" if is_web else "/server_config"
        try:
            await sp_call_with_retry(
                self.page.push_route,
                target_route,
                retries=2,
                delay=0.3,
                per_call_timeout=3.0,
            )
        except Exception as e:
            print(f"Hard reset: push_route({target_route!r}) failed: {e}")
            splash.set_progress(
                1, "Navigation failed - please restart the app"
            )
