"""
Home search utility for managing home search data
"""

import flet as ft


class HomeSearch:
    """Home search manager for storing and retrieving home search data"""

    def __init__(self, page: ft.Page):
        """
        Initialize home search manager

        Args:
            page: The Flet page
        """
        self.page = page
        if not hasattr(page, "data") or page.data is None:
            page.data = {}

        page.data.setdefault("home_search", "")

    def set(self, search_value: str):
        """
        Store home search value in page data

        Args:
            search_value: The search string to store
        """
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}

        self.page.data["home_search"] = search_value

    def get(self) -> str:
        """
        Retrieve home search value from page data

        Returns:
            str: The stored search string or empty string if not set
        """
        if not hasattr(self.page, "data") or self.page.data is None:
            return ""

        return self.page.data.get("home_search", "")

    def clear(self):
        """Clear the stored home search value"""
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}

        self.page.data.pop("home_search", None)
