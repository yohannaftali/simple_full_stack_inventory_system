import flet as ft

from repository.storage import Storage


class HomeSearchBar:
    """Home search bar component"""

    def __init__(
        self,
        page: ft.Page,
        modules: list,
        on_filter_change=None,
        on_submit=None,
        initial_value: str = "",
    ):
        """
        Initialize home search bar

        Args:
            page: The Flet page
            modules: List of all modules
            on_filter_change: Callback function when filtered modules change
            on_submit: Callback function when Enter key is pressed
        """
        self.page = page
        self.storage: Storage = page.data["storage"]
        self.modules = modules
        self.filtered_modules = modules.copy()
        self.on_filter_change = on_filter_change
        self.on_submit = on_submit

        # Search bar
        # Persisted starting value
        self.search_bar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.Colors.TERTIARY,
            bar_hint_text="Search modules...",
            view_hint_text="Choose a module from suggestions...",
            on_change=self.on_search_change,
            on_submit=self.on_search_submit,
            value=initial_value,
            # Material 3 Search bar spec: surfaceContainerHigh background,
            # onSurface content - a subtly-elevated neutral container, not a
            # colored accent (that's the older M2 convention).
            bar_bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            bar_text_style=ft.TextStyle(color=ft.Colors.ON_SURFACE, size=14),
            # Lighter than `bar_text_style`'s entered-text color, so the
            # placeholder is visibly distinguishable from real input
            # (issue #19 - same fix as the table search bar's `hint_style`).
            bar_hint_text_style=ft.TextStyle(
                color=ft.Colors.with_opacity(0.5, ft.Colors.ON_SURFACE), size=14
            ),
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
                    icon_size=20,
                    on_click=self.clear_search,
                )
            ],
        )

        # No `expand=True` here: this container is a direct child of the
        # home body's Column (components/home/body.py), where `expand` on a
        # child governs the Column's *main* (vertical) axis share, not
        # width - it would make the search bar fight the module grid/footer
        # for vertical space instead of just sizing to its own content
        # height. Full width comes from that Column's
        # `horizontal_alignment=STRETCH` instead.
        self.container = ft.Container(content=self.search_bar, padding=20)

    def build(self):
        """Build and return the search bar control"""
        return self.container

    def on_search_change(self, e):
        """Handle search input change"""
        search_text = self.search_bar.value.lower()
        # Persist value to page.data if page available
        self.storage.home_search.set(self.search_bar.value)
        # if self.search_bar.page and hasattr(self.search_bar.page, "data") and isinstance(self.search_bar.page.data, dict):
        #     self.search_bar.page.data["home_search"] = self.search_bar.value

        if not search_text:
            self.filtered_modules = self.modules.copy()
        else:
            self.filtered_modules = [
                module
                for module in self.modules
                if search_text in module.get("label", "").lower()
                or (module.get("group") and search_text in module["group"].lower())
            ]

        # Notify parent of filter change
        if self.on_filter_change:
            self.on_filter_change(self.filtered_modules)

    def clear_search(self, e):
        """Clear search field"""
        self.search_bar.value = ""
        self._safe_update()
        self.filtered_modules = self.modules.copy()
        self.storage.home_search.set("")

        # Notify parent of filter change
        if self.on_filter_change:
            self.on_filter_change(self.filtered_modules)

    def _safe_update(self):
        """Update the search bar if it's already mounted on the page."""
        try:
            self.search_bar.update()
        except RuntimeError:
            pass

    def update_modules(self, modules: list):
        """Update the modules list"""
        self.modules = modules
        # Preserve current search value and reapply filtering
        current_value = self.search_bar.value
        if current_value:
            # Recompute filtered list using existing search text
            lowered = current_value.lower()
            self.filtered_modules = [
                module
                for module in self.modules
                if lowered in module.get("label", "").lower()
                or (module.get("group") and lowered in module["group"].lower())
            ]
        else:
            self.filtered_modules = self.modules.copy()
        # Persist value in page.data if available
        self.storage.home_search.set(current_value)

    def get_filtered_modules(self):
        """Get the current filtered modules"""
        return self.filtered_modules

    def on_search_submit(self, e):
        """Handle Enter key press in search bar"""
        if self.on_submit and self.filtered_modules:
            # Navigate to first filtered module
            self.on_submit(self.filtered_modules[0])
