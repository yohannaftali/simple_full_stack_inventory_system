import flet as ft

from repository.storage import Storage


class TableSearchBar:
    """Table search bar component"""

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
            # Material 3 Search bar spec: surfaceContainerHigh background,
            # onSurface content - a subtly-elevated neutral container, not a
            # colored accent (that's the older M2 convention).
            bar_bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            bar_text_style=ft.TextStyle(color=ft.Colors.ON_SURFACE, size=14),
            # A ControlState dict of low-opacity tints (the M3 "state layer"
            # convention), not a single solid color: passing a plain color
            # here replaces the whole bar background on hover/focus/press
            # instead of tinting it, which is why the bar used to turn
            # solid near-black in light mode / near-white in dark mode
            # (on_surface at full opacity) with same-colored, invisible text
            # on top.
            bar_overlay_color={
                ft.ControlState.HOVERED: ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                ft.ControlState.FOCUSED: ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE),
                ft.ControlState.PRESSED: ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE),
            },
            bar_leading=ft.Icon(ft.Icons.SEARCH, color=ft.Colors.ON_SURFACE, size=14),
            view_leading=ft.Icon(ft.Icons.SEARCH, color=ft.Colors.ON_SURFACE, size=14),
            bar_trailing=[
                ft.IconButton(
                    icon=ft.Icons.CLEAR,
                    icon_color=ft.Colors.ON_SURFACE,
                    icon_size=14,
                    on_click=self.clear_search,
                )
            ],
            view_trailing=[
                ft.IconButton(
                    icon=ft.Icons.CLEAR,
                    icon_color=ft.Colors.ON_SURFACE,
                    icon_size=14,
                    on_click=self.clear_search,
                )
            ],
        )

        # No `alignment` here deliberately: a Container with `alignment` set
        # gives its child loose constraints (size yourself, then I'll
        # position you), so SearchBar - which has no `expand` of its own
        # (it's a LayoutControl, not a ConstrainedControl) - shrinks to its
        # own intrinsic width and gets centered instead of filling the row.
        # Without `alignment`, the container passes its own (expanded) size
        # to the child directly, forcing it full width on every screen size.
        self.container = ft.Container(content=self.search_bar, padding=0, expand=True)

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
