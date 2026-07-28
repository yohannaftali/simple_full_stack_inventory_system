import flet as ft

from repository.storage import Storage


class ListSearchBar:
    """List search bar component, rebuilt on a plain `ft.TextField` (issue
    #56) - the same fix `components/table/search_bar.py::TableSearchBar`
    already received under issue #19, for the same reason: Flutter's own
    `ft.SearchBar` is a rigid ~56dp Material widget that doesn't genuinely
    fill/expand to its container's width the way a plain `TextField` does,
    which is exactly why `Table`'s own search bar was rebuilt away from it
    and `List`'s never was until now."""

    def __init__(self, page: ft.Page, parent, on_filter_change=None, on_submit=None, initial_value: str = ""):
        """
        Initialize list search bar

        Args:
            on_search_change: Callback function when search value changes
            on_submit: Callback function when Enter key is pressed
        """
        self.page = page
        self.storage: Storage = page.data["storage"]
        self.parent = parent
        self.on_filter_change = on_filter_change
        self.on_submit = on_submit

        clear_button = ft.IconButton(
            icon=ft.Icons.CLEAR,
            icon_color=ft.Colors.ON_SURFACE,
            icon_size=14,
            width=24,
            height=24,
            padding=0,
            on_click=self.clear_search,
            tooltip="Clear text",
            # Matches TableSearchBar's own fix - without this, Flutter
            # reserves its default ~48dp tap-target for the icon, pushing it
            # past the field's true right edge (issue #19).
            size_constraints=ft.BoxConstraints(
                min_width=24, max_width=24, min_height=24, max_height=24
            ),
        )

        self.search_bar = ft.TextField(
            value=initial_value,
            hint_text="Search in list...",
            hint_style=ft.TextStyle(
                color=ft.Colors.with_opacity(0.5, ft.Colors.ON_SURFACE), size=13
            ),
            height=32,
            text_size=13,
            text_vertical_align=ft.VerticalAlignment.CENTER,
            on_change=self.on_search_change,
            on_submit=self.on_submit,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            color=ft.Colors.ON_SURFACE,
            border_radius=10,
            border_color=ft.Colors.OUTLINE_VARIANT,
            focused_border_color=ft.Colors.TERTIARY,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            prefix_icon=ft.Icon(ft.Icons.SEARCH, color=ft.Colors.ON_SURFACE, size=14),
            suffix_icon=clear_button,
            suffix_icon_size_constraints=ft.BoxConstraints(
                min_width=24, max_width=24, min_height=24, max_height=24
            ),
            expand=True,
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
