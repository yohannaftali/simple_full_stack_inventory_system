import asyncio

import flet as ft

from repository.client_data import ClientData
from repository.home_search import HomeSearch
from repository.http_cookies import HttpCookies
from repository.module_history import ModuleHistory
from repository.server_url import ServerURL
from repository.table_search import TableSearch
from repository.theme_mode import ThemeMode
from repository.user_session import UserSession
from utils.persistence import make_session_store


class Storage:
    """Session storage utility with a platform-appropriate persistence backend.

    Native (desktop/Android/iOS) persists to a JSON file (reliable, durable);
    web uses Flet's SharedPreferences service. See utils/persistence.py.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        if not hasattr(page, "data") or page.data is None:
            page.data = {}

        # Only web needs the SharedPreferences service (whose async
        # method-channel listener is unreliable on cold-start - the source of
        # the desktop "logged out on module open" bug). Native platforms skip
        # it entirely and persist to a file instead, avoiding the timeout hangs.
        self.sp = None
        if bool(getattr(page, "web", False)):
            self.sp = ft.SharedPreferences()
            page.services.append(self.sp)
            page.update()

        self.store = make_session_store(page, self.sp)

        # Persistent
        self.http_cookies = HttpCookies(page, self.store)
        self.theme_mode = ThemeMode(page, self.store)
        self.server_url = ServerURL(page, self.store)
        self.user_session = UserSession(page, self.store)
        page.data["storage"] = self

        # Non Persistent
        self.client_data = ClientData(page)
        self.module_history = ModuleHistory(page)
        self.home_search = HomeSearch(page)
        self.table_search = TableSearch(page)

    async def load_persistent(self):
        """Load all persistent (SharedPreferences-backed) values into the
        in-memory page.data cache. Must be awaited once at startup, before
        any persistent getter (server_url.get(), theme_mode.get(), etc.) is
        relied upon, since SharedPreferences access is async-only.

        The four loads are run concurrently: each hits an independent
        SharedPreferences key and, when the client's service listener isn't
        ready (notably web mode - see
        utils/storage_compat.py::sp_call_with_retry), each falls back to a
        default after its own short retry budget. Running them in parallel
        means startup waits at most one key's budget instead of the sum of
        all of them. Every load() swallows its own exceptions, so
        `return_exceptions=True` is just belt-and-suspenders."""
        await asyncio.gather(
            self.http_cookies.load(),
            self.theme_mode.load(),
            self.server_url.load(),
            self.user_session.load(),
            return_exceptions=True,
        )

    def set(self, key: str, value):
        """Store a value in session (page.data + client_storage for persistent keys)"""
        self.page.data[key] = value

    def get(self, key: str, default=None):
        """Retrieve a value from session (page.data)"""
        return self.page.data.get(key, default)

    def remove(self, key: str):
        """Remove a value from session (page.data)"""
        self.page.data.pop(key, None)

    def contains(self, key: str) -> bool:
        """Check if a key exists in storage (page.data)"""
        return key in self.page.data

    def clear(self):
        """Clear user session from page.data and persistent cookies"""
        self.user_session.clear()
        self.client_data.clear()
        self.http_cookies.clear()
        self.module_history.clear()
        self.home_search.clear()
        self.table_search.clear()

    async def clear_all_persistent(self):
        """Hard reset: wipe every SharedPreferences-backed key (server url,
        theme, login session/cookies) in one shot and reset their in-memory
        mirrors. Used by the Troubleshooting page's "Clear Shared
        Preferences" button. Unlike `hard_reset()`, this keeps
        `page.data["storage"]` itself intact, so the rest of the running
        app keeps working and can navigate to /login normally afterwards."""
        try:
            if self.sp:
                await self.sp.clear()
        except Exception as e:
            print(f"Could not clear SharedPreferences: {e}")

        self.user_session.clear()
        self.client_data.clear()
        self.http_cookies.clear()

        # Clear the in-memory mirrors of the other persistent keys too, so
        # the app doesn't keep using stale values after the SharedPreferences
        self.theme_mode.clear()

        self.theme_mode.apply("light")  # Reset to default theme after clearing
        self.page.update()  # Ensure the theme change is reflected immediately

        # Clear the non-persistent keys too, so the app is fully reset to a clean state
        self.server_url.clear()
        self.module_history.clear()
        self.home_search.clear()
        self.table_search.clear()

    def reset(self):
        """Clear all data except storage"""
        keys_to_remove = [k for k in self.page.data.keys() if k != "storage"]
        for key in keys_to_remove:
            self.page.data.pop(key, None)

    def hard_reset(self):
        """Clear all data including storage"""
        self.page.data = {}
