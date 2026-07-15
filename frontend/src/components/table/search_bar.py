import flet as ft

from repository.storage import Storage


class TableSearchBar:
    """Table search bar component built for compact 32dp layout bars"""

    def __init__(
        self,
        page: ft.Page,
        parent,
        on_filter_change=None,
        on_submit=None,
        initial_value: str = "",
    ):
        """
        Initialize table search bar

        Args:
            page: The Flet page
            parent: The calling module parent reference
            on_filter_change: Callback function when search value changes
            on_submit: Callback function when Enter key is pressed
            initial_value: Initial seed text string
        """
        self.page = page
        self.storage: Storage = page.data["storage"]
        self.parent = parent
        self.on_filter_change = on_filter_change
        self.on_submit = on_submit

        # Compact Text Field Configuration replacing the rigid 56dp ft.SearchBar
        self.search_bar = ft.TextField(
            value=initial_value,
            hint_text="Search in table...",
            height=32,  # Hard-locked compact dimension profile
            text_size=13,  # Scaled down to prevent text vertical wrapping
            on_change=self.on_search_change,
            on_submit=self.on_submit,
            # Material 3 Styling mapping to your exact Theme values
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            color=ft.Colors.ON_SURFACE,
            border_radius=8,
            # Low opacity state-layer boundaries matching your architectural commentary
            border_color=ft.Colors.OUTLINE_VARIANT,
            focused_border_color=ft.Colors.TERTIARY,
            # Content padding adjustment prevents the text block from drifting out of alignment
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=0),
            # Functional Iconography alignments scaled down to match the 32dp boundary constraints
            prefix=ft.Icon(ft.Icons.SEARCH, color=ft.Colors.ON_SURFACE, size=14),
            suffix=ft.IconButton(
                icon=ft.Icons.CLEAR,
                icon_color=ft.Colors.ON_SURFACE,
                icon_size=14,
                width=24,  # Constrained icon button envelope bounds
                height=24,
                padding=0,  # Absolute graphic centering
                on_click=self.clear_search,
                tooltip="Clear text",
            ),
        )

        self.container = ft.Container(
            content=self.search_bar,
            padding=0,
            expand=True,
        )

    def build(self):
        """Build and return the search bar control"""
        return self.container

    def on_search_change(self, e):
        """Handle search input change"""
        search_text = self.search_bar.value.lower()
        # Persist value to page.data if page available
        self.storage.table_search.set(
            self.parent.module,
            self.parent.screen,
            self.parent.name,
            self.search_bar.value,
        )

        # Notify parent of filter change
        if self.on_filter_change:
            self.on_filter_change(search_text)

    def clear_search(self, e):
        """Clear the search bar value"""
        self.search_bar.value = ""
        self._safe_update()
        self.storage.table_search.set(
            self.parent.module, self.parent.screen, self.parent.name, ""
        )

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
