"""
Theme Mode class for managing theme mode data
"""

import flet as ft

from themes.dark_theme import DarkTheme
from themes.light_theme import LightTheme
from utils.storage_compat import unwrap_legacy_value


class ThemeMode:
    """Theme Mode manager for storing and retrieving theme mode data"""

    def __init__(self, page: ft.Page, store=None):
        """
        Initialize theme mode manager
        Args:
            page: The Flet page
            store: Session persistence backend (see utils/persistence.py).
                Optional - callers that only need to read the cached value
                don't need to provide it.
        """
        self.page = page
        self.store = store
        if not hasattr(page, "data") or page.data is None:
            page.data = {}
        page.data.setdefault("theme_mode", "")

        self.page.theme = LightTheme.get_theme()
        self.page.dark_theme = DarkTheme.get_theme()

        # fallback to default theme mode if not set
        current_cached = self.page.data.get("theme_mode", "light")
        self.apply(current_cached if current_cached != "" else "light")

    def set(self, value: str):
        """
        Store theme mode value
        Args:
            value: The theme mode to store
        """
        self.page.data["theme_mode"] = value
        self.apply(value)

        self.page.update()

        if self.store:
            self.store.persist("theme_mode", value)

    def get(self) -> str:
        """
        Retrieve theme mode value from the in-memory cache (populated at
        startup by `load()`)

        Returns:
            str: The stored theme mode string or "light" if not set
        """
        if "theme_mode" in self.page.data and self.page.data["theme_mode"] != "":
            return self.page.data["theme_mode"]

        # Fallback to default
        self.page.data["theme_mode"] = "light"
        return "light"

    def clear(self):
        """Clear the stored theme mode value"""
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}
        self.page.data["theme_mode"] = ""

        if self.store:
            self.store.forget("theme_mode")

    async def load(self):
        """Load the persisted theme mode from the session store (async)"""
        theme_mode = None

        if self.store:
            try:
                theme_mode = await self.store.load("theme_mode")
            except Exception as e:
                print(f"Could not load theme_mode from session store: {e}")

        theme_mode = unwrap_legacy_value(theme_mode)
        if theme_mode and theme_mode != "":
            self.page.data["theme_mode"] = theme_mode
        else:
            self.page.data["theme_mode"] = "light"

        self.apply(self.page.data["theme_mode"])

        self.page.update()
        print(f"Theme mode: {self.page.data['theme_mode']}")

    def apply(self, theme_mode: str):
        if theme_mode == "light":
            self.page.theme_mode = ft.ThemeMode.LIGHT
        elif theme_mode == "dark":
            self.page.theme_mode = ft.ThemeMode.DARK
        else:
            self.page.theme_mode = ft.ThemeMode.SYSTEM

    def toggle(self):
        current_theme = self.get()
        new_theme = "dark" if current_theme == "light" else "light"
        self.set(new_theme)
        print(f"Theme switched to: {new_theme}")
        return new_theme
