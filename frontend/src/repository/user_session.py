"""
User Session class for managing user session data
"""
import asyncio

import flet as ft

from utils.storage_compat import unwrap_legacy_value


class UserSession:
    """User Session manager for storing and retrieving user session data"""

    def __init__(self, page: ft.Page, store=None):
        """
        Initialize user session manager
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
        page.data.setdefault("user_session", {})
        self.username = ""
        self.is_logged_in = False
        self.token = None

    def set(self, username: str, token: str = None):
        """
        Store theme mode value
        Args:
            value: The theme mode to store
        """
        self.username = username
        self.is_logged_in = True
        self.token = token

        self.page.data["user_session"] = {
            "username": username,
            "is_logged_in": "true",
            "token": token
        }

        self.store.persist("username", username)
        self.store.persist("is_logged_in", "true")
        self.store.persist("token", token if token else "")

    def get(self, key: str) -> str:
        """
        Retrieve user session from page.data
        Args:
            key: Key to retrieve from user session
        Returns:
            str: The stored user session string or empty string if not set
        """
        # Check if already loaded in page.data (populated at startup by
        # `load()`, or via `set()` during login)
        if key in self.page.data["user_session"]:
            value = self.page.data["user_session"][key]
            setattr(self, key, value)
            return value

        self.page.data["user_session"][key] = ""
        setattr(self, key, "")
        return ""

    async def load(self):
        """Lazy loading data from SharedPreferences (async)"""
        # NOTE: "is_logged_id" (not "is_logged_in") matches the original
        # pre-migration code exactly - kept as-is to preserve behavior.
        # The three keys are loaded concurrently so a not-yet-ready client
        # (see utils/storage_compat.py::sp_call_with_retry) costs one key's
        # retry budget total, not three sequential budgets.
        keys = ("username", "is_logged_id", "token")
        await asyncio.gather(*(self._load_key(key) for key in keys))

    async def _load_key(self, key: str):
        value = None
        try:
            value = await self.store.load(key)
        except Exception as e:
            print(f"Could not load {key} from session store: {e}")

        value = unwrap_legacy_value(value)
        if value:
            self.page.data["user_session"][key] = value
            setattr(self, key, value)
        else:
            self.page.data["user_session"][key] = ""
            setattr(self, key, "")

    def clear(self):
        """Clear the user session dictionary"""
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}

        self.page.data.pop("user_session", None)
        self.username = ""
        self.is_logged_in = False
        self.token = None

        self.store.forget("username")
        self.store.forget("is_logged_in")
        self.store.forget("token")
