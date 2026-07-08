import flet as ft

from repository.storage import Storage


class TableSearchBar:
    """Table search bar component"""

    def __init__(self, page: ft.Page, parent, on_filter_change=None, on_submit=None, initial_value: str = ""):
        """
        Initialize table search bar

        Args:
            on_search_change: Callback function when search value changes
            on_submit: Callback function when Enter key is pressed
        """
        self.page = page
        self.storage: Storage = page.data["storage"]
        self.parent = parent
        self.on_filter_change = on_filter_change
        self.on_submit = on_submit

        # Search bar
        # Persisted starting value
        self.search_bar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.Colors.TERTIARY,
            bar_hint_text="Search in table...",
            view_hint_text="Choose an option from filter...",
            on_change=self.on_search_change,
            on_submit=self.on_submit,
            value=initial_value,
            bar_bgcolor=ft.Colors.SECONDARY,
            bar_text_style=ft.TextStyle(color=ft.Colors.ON_SECONDARY, size=14),
            bar_overlay_color=ft.Colors.PRIMARY,
            bar_leading=ft.Icon(
                ft.Icons.SEARCH, color=ft.Colors.ON_SECONDARY, size=14),
            view_leading=ft.Icon(
                ft.Icons.SEARCH, color=ft.Colors.ON_PRIMARY, size=14),
            bar_trailing=[ft.IconButton(
                icon=ft.Icons.CLEAR,
                icon_color=ft.Colors.ON_SECONDARY,
                icon_size=14,
                on_click=self.clear_search,
            )],
            view_trailing=[ft.IconButton(
                icon=ft.Icons.CLEAR,
                icon_color=ft.Colors.ON_PRIMARY,
                icon_size=14,
                on_click=self.clear_search,
            )],
        )

        self.container = ft.Container(
            content=self.search_bar,
            padding=0,
            alignment=ft.Alignment.CENTER,
            expand=True
        )

    def build(self):
        """Build and return the search bar control"""
        return self.container

    def on_search_change(self, e):
        """Handle search input change"""
        search_text = self.search_bar.value.lower()
        # Persist value to page.data if page available
        self.storage.table_search.set(
            self.parent.module, self.parent.screen, self.parent.name, self.search_bar.value)

        # Notify parent of filter change
        if self.on_filter_change:
            self.on_filter_change(search_text)

    def clear_search(self, e):
        """Clear the search bar value"""
        self.search_bar.value = ""
        self._safe_update()
        self.storage.table_search.set(
            self.parent.module, self.parent.screen, self.parent.name, "")

        # Notify parent of filter change
        if self.on_filter_change:
            self.on_filter_change("")
            self.parent.on_submit(e)

    def _safe_update(self):
        """Update the search bar if it's already mounted on the page."""
        try:
            self.search_bar.update()
        except RuntimeError:
            pass
