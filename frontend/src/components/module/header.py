"""
Header component for the module
"""

import flet as ft

from components.button import TOUCH_TARGET_SIZE
from components.home.user_menu import UserMenu

# M3 Small top app bar container height (issue #83) - Flutter's own
# un-overridden default (`kToolbarHeight`) is 56dp, a Material 2-era
# constant; M3's spec is 64dp.
APPBAR_HEIGHT_SMALL = 64
# Not a true M3 "Medium" flexible/collapsing app bar (Flet's ft.AppBar has
# no Sliver/FlexibleSpaceBar support at all - confirmed by reading the
# installed package source, see issue #83) - just a taller fixed Small bar
# with room for a 2-line wrapped headline under the module-name subtitle
# line, used whenever a page has both.
APPBAR_HEIGHT_TWO_LINE = 88


class ModuleHeader:
    """Header AppBar component"""

    def __init__(self, page: ft.Page, module_label: str = "Module"):
        """
        Initialize header

        Args:
            page: The Flet page
            module_label: the module's own display name (issue #83) - shown
                as a smaller subtitle line above the page-specific title, so
                a screen visually identifies which module it belongs to.
                Set once by ModuleView at construction time; individual
                screens only ever change the page title via set_title().
        """
        self.page = page

        # Material 3 top app bars use a neutral surface color, not primary -
        # unlike the home page's own AppBar (components/home/header.py),
        # which still uses primary.
        self.user_menu = UserMenu(page)
        self.module_label = module_label
        # Blank until a screen calls set_title() - an index screen never
        # does, so its AppBar shows the module name alone as a single line
        # (see _build_title_control()) rather than a redundant "Module /
        # Module" two-line block.
        self.title = ""

    def _build_title_control(self) -> ft.Control:
        """Single line (module name only) when no page-specific title has
        been set yet, or when it's identical to the module name; otherwise
        a two-line, start-aligned block - module name as the smaller
        supporting-text line, page title as the headline, wrapped to a
        maximum of 2 lines (issue #83's "long headline" case) rather than
        truncated to one."""
        if not self.title or self.title == self.module_label:
            return ft.Text(
                self.module_label,
                color=ft.Colors.ON_SURFACE,
                size=16,
                weight=ft.FontWeight.W_500,
            )
        return ft.Column(
            controls=[
                ft.Text(
                    self.module_label,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    size=12,
                ),
                ft.Text(
                    self.title,
                    color=ft.Colors.ON_SURFACE,
                    size=16,
                    weight=ft.FontWeight.W_500,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=0,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    def build(self):
        """Build and return the AppBar"""
        is_two_line = bool(self.title) and self.title != self.module_label
        actions = [
            ft.IconButton(
                icon=ft.Icons.HOME,
                icon_color=ft.Colors.ON_SURFACE,
                icon_size=24,
                width=TOUCH_TARGET_SIZE,
                height=TOUCH_TARGET_SIZE,
                tooltip="Home",
                on_click=self.on_home_click,
            )
        ]
        if self.user_menu:
            actions.append(self.user_menu.build())

        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.ON_SURFACE,
                icon_size=24,
                # leading_width below only bounds the slot's *width* - its
                # height still stretches to the toolbar's full height, so
                # the button's own hover/splash ripple fills that taller
                # box unless explicitly pinned to match the action icons'
                # tightly-wrapped 48x48 M3 touch-target footprint.
                width=TOUCH_TARGET_SIZE,
                height=TOUCH_TARGET_SIZE,
                tooltip="Back",
                on_click=self.on_click,
            ),
            # AppBar.leading otherwise gets a 56px-wide slot by default
            # (Flutter's kToolbarHeight), noticeably wider than the ~48px
            # tap-target box the action icons naturally get - same icon_size,
            # but the back button's whole clickable/visual footprint ends up
            # bigger. Match it to the standard Material icon-button size.
            leading_width=TOUCH_TARGET_SIZE,
            title=self._build_title_control(),
            # M3's Small top app bar aligns title/subtitle to the start,
            # not centered (issue #83) - center_title=True was this app's
            # leftover Material 2 default.
            center_title=False,
            toolbar_height=APPBAR_HEIGHT_TWO_LINE if is_two_line else APPBAR_HEIGHT_SMALL,
            bgcolor=ft.Colors.SURFACE,
            actions=actions,
            elevation=0,
            elevation_on_scroll=0,
            shadow_color=ft.Colors.SHADOW,
        )

    def set_title(self, title: str):
        """Set the page-specific title (headline line) of the AppBar - the
        module-name subtitle line is set once at construction and never
        changes."""
        self.title = title

    def on_click(self, e):
        """Navigate back within module screens or to home if history exhausted."""
        if hasattr(self.page, "banner") and self.page.banner:
            self.page.banner.open = False
            self.page.update()

        history = []
        if hasattr(self.page, "data") and isinstance(self.page.data, dict):
            history = self.page.data.get("module_history", [])
        current_screen = history[-1][1] if history else None
        if history:
            history.pop()
        # Leaving an index screen means leaving the module entirely - drop
        # the rest of the stack instead of surfacing whatever module was
        # visited before this one.
        if current_screen == "index" or not history:
            self.page.data["module_history"] = []
            self.page.run_task(self.page.push_route, "/home")
        else:
            prev_module, prev_screen, prev_record_id = history[-1]
            self.page.data["module_history"] = history
            route = f"/modules/{prev_module}/{prev_screen}"
            if prev_record_id is not None:
                route += f"/{prev_record_id}"
            self.page.run_task(self.page.push_route, route)

    def on_home_click(self, e):
        """Navigate back to home"""
        if hasattr(self.page, "banner") and self.page.banner:
            self.page.banner.open = False
            self.page.update()

        self.page.run_task(self.page.push_route, "/home")
