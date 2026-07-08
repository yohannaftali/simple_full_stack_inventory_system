"""
Home search utility for managing home search data
"""

import flet as ft


class TableSearch:
    """Table search manager for storing and retrieving table search data"""

    def __init__(self, page: ft.Page):
        """
        Initialize table search manager

        Args:
            page: The Flet page
        """
        self.page = page
        if not hasattr(page, "data") or page.data is None:
            page.data = {}

        page.data.setdefault("table_search", {})

    def set(self, module: str, screen: str, name: str, search_value: str):
        """
        Store table search value in page data. Values are stored as strings
        because this repository is used only for table search bar text.

        Args:
            search_value: The search value to store (will be coerced to string)
        """
        # Ensure page.data exists and is a dict
        pdata = getattr(self.page, "data", None)
        if pdata is None or not isinstance(pdata, dict):
            pdata = {}
            self.page.data = pdata

        # Ensure nested structure exists using setdefault chains
        pdata.setdefault("table_search", {})
        pdata["table_search"].setdefault(module, {})
        pdata["table_search"][module].setdefault(screen, {})

        # Coerce value to string to guarantee consumers get a string
        if search_value is None:
            sval = ""
        else:
            try:
                sval = str(search_value)
            except Exception:
                sval = ""

        pdata["table_search"][module][screen][name] = sval

    def get(self, module: str, screen: str, name: str) -> str:
        """
        Retrieve table search value from page data
        Args:
            module: The module name
            screen: The screen name
            name: The table name
        Returns:
            str: The stored search string or empty string if not set
        """
        # Defensive fetch using dict.get chains. Return empty string when not present.
        pdata = getattr(self.page, "data", None)
        if not isinstance(pdata, dict):
            return ""

        ts = pdata.get("table_search")
        if not isinstance(ts, dict):
            return ""

        val = ts.get(module, {}).get(screen, {}).get(name, "")
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        # Coerce non-string values to string representation
        try:
            return str(val)
        except Exception:
            return ""

    def clear(self):
        """Clear the stored table search value"""
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}

        self.page.data.pop("table_search", None)
