"""
HTTP Cookies data for managing HTTP Cookies data
"""

import json
import flet as ft

from utils.storage_compat import unwrap_legacy_value


class HttpCookies:
    """Server URL manager for storing and retrieving HTTP Cookies data"""

    def __init__(self, page: ft.Page, store=None):
        """
        Initialize HTTP Cookies manager
        Args:
            page: The Flet page
            store: Session persistence backend (see utils/persistence.py).
                Optional - callers that only need to read the cached value
                (e.g. HttpClient) don't need to provide it.
        """
        self.page = page
        self.store = store
        if not hasattr(page, "data") or page.data is None:
            page.data = {}

    def set(self, cookies: dict):
        """
        Store HTTP Cookies value

        Args:
            value: The HTTP Cookies to store
        """
        cookies_str = json.dumps(cookies) or ""
        self.page.data["http_cookies"] = cookies_str
        self.store.persist("http_cookies", cookies_str)

    def get(self) -> dict | None:
        """
        Retrieve HTTP Cookies value from the in-memory cache (populated at
        startup by `load()`)

        Returns:
            dict | None: The stored HTTP Cookies dictionary or None if not set
        """
        if "http_cookies" in self.page.data:
            cookies_str = self.page.data["http_cookies"]
            if cookies_str and cookies_str != "":
                return json.loads(cookies_str)
            return None

        return None

    def clear(self):
        """Clear the stored http cookies value"""
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}

        # Clear persistent cookies from page.data
        self.page.data.pop("http_cookies", None)

        self.store.forget("http_cookies")

    async def load(self):
        """Load the persisted http cookies from the session store (async)"""
        cookies_str = None
        try:
            cookies_str = await self.store.load("http_cookies")
        except Exception as e:
            print(f"Could not load http cookies from session store: {e}")

        cookies_str = unwrap_legacy_value(cookies_str)
        if cookies_str and cookies_str != "":
            self.page.data["http_cookies"] = cookies_str
        else:
            self.page.data["http_cookies"] = ""
