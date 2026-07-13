import flet as ft


class ModuleHistory:
    """Module history manager for tracking navigation history."""

    def __init__(self, page: ft.Page):
        """
        Initialize module history manager

        Args:
            page: The Flet page
        """
        self.page = page
        if not hasattr(page, "data") or page.data is None:
            page.data = {}

        page.data.setdefault("module_history", [])

    def add(self, module: str, screen: str, record_id: str = None):
        """
        Add a module/screen entry to the history

        Args:
            module: Module name
            screen: Screen name
            record_id: Optional record id from the route, so a back
                navigation can return to the exact same record
        """
        history = self.page.data.get("module_history", [])
        entry = (module, screen, record_id)
        if not history or history[-1] != entry:
            history.append(entry)

        self.page.data["module_history"] = history

    def get(self):
        """
        Get the current module history

        Returns:
            list: List of (module, screen) tuples
        """
        return self.page.data.get("module_history", [])

    def clear(self):
        """Clear the stored module history array"""
        if not hasattr(self.page, "data") or self.page.data is None:
            self.page.data = {}

        self.page.data.pop("module_history", None)
