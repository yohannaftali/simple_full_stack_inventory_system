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

    def add(self, module: str, screen: str):
        """
        Add a module/screen entry to the history

        Args:
            module: Module name
            screen: Screen name
        """
        history = self.page.data.get("module_history", [])
        if not history or history[-1] != (module, screen):
            history.append((module, screen))

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
