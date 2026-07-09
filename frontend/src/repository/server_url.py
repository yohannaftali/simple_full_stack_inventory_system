"""
Server URL data for managing server URL data
"""

import flet as ft

from utils.storage_compat import unwrap_legacy_value


# Default backend address for the containerized deployment: "backend" is
# the compose service's DNS name on the podman-compose network, reachable
# from inside sfsis-frontend but NOT from a browser/native client outside
# that network (there, use the published host port instead, e.g.
# http://localhost:5000 or https://localhost:5443). Doubles as the
# "never configured" sentinel in main.py's _boot_navigate - if you change
# this to something that resolves for every deployment target, that
# force-to-/server_config behavior effectively disables itself.
DEFAULT_SERVER_URL = "http://backend:5000"


class ServerURL:
    """Server URL manager for storing and retrieving server URL data"""

    def __init__(self, page: ft.Page, store=None):
        """
        Initialize server URL manager
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
        page.data.setdefault("server_url", "")

    def set(self, value: str):
        """
        Store server url value

        Args:
            value: The server URL to store
        """
        self.page.data["server_url"] = value
        self.store.persist("server_url", value)

    def get(self) -> str:
        """
        Retrieve base server url value from the in-memory cache (populated
        at startup by `load()`)

        Returns:
            str: The stored base server url string or the default if not set
        """
        if "server_url" in self.page.data and self.page.data["server_url"] != "":
            return self.page.data["server_url"]

        # Fallback to default
        self.page.data["server_url"] = DEFAULT_SERVER_URL
        return DEFAULT_SERVER_URL

    def clear(self):
        """Clear the stored base server url value"""
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}
        self.page.data["server_url"] = ""

        self.store.forget("server_url")

    async def load(self):
        """Load the persisted server url from the session store (async)"""
        server_url = None
        try:
            server_url = await self.store.load("server_url")
        except Exception as e:
            print(f"Could not load server_url from session store: {e}")

        server_url = unwrap_legacy_value(server_url)
        if server_url and server_url != "":
            self.page.data["server_url"] = server_url
        else:
            self.page.data["server_url"] = DEFAULT_SERVER_URL

        print(f"Server url: {self.page.data['server_url']}")
