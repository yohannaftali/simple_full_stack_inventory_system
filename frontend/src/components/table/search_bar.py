import flet as ft

from components.scan_input import ScanInput
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
        qr: bool = False,
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
        # Opt-in barcode/QR scan button (issue #52) - off by default, so
        # every other table's search bar is unchanged.
        self.qr = qr
        self.scan_input: ScanInput | None = None

        clear_button = ft.IconButton(
            icon=ft.Icons.CLEAR,
            icon_color=ft.Colors.ON_SURFACE,
            icon_size=14,
            width=24,  # Constrained icon button envelope bounds
            height=24,
            padding=0,  # Absolute graphic centering
            on_click=self.clear_search,
            tooltip="Clear text",
        )
        if self.qr:
            # The QR button sits to the LEFT of the clear/X, inside the same
            # suffix slot, since suffix_icon takes a single control. The
            # width constraints below are widened to fit both - they exist to
            # stop Flutter reserving its default ~48dp tap target per icon,
            # which is what pushed the clear icon past the field's right edge
            # in issue #19, so they must track the real content width rather
            # than being dropped.
            self.scan_input = ScanInput(
                page=page,
                on_scan=self._apply_scanned_code,
                title="Scan to Search",
                tooltip="Scan barcode / QR to search",
                icon_size=14,
                width=24,
                height=24,
            )
            suffix_control = ft.Row(
                controls=[self.scan_input.build(), clear_button],
                spacing=0,
                tight=True,
            )
            suffix_width = 48
        else:
            suffix_control = clear_button
            suffix_width = 24

        # Compact Text Field Configuration replacing the rigid 56dp ft.SearchBar
        self.search_bar = ft.TextField(
            value=initial_value,
            hint_text="Search in table...",
            # Lighter than the entered-text color (`color` below) so the
            # placeholder is visibly distinguishable from real input, not a
            # near-identical shade of the same on-surface color (issue #19).
            hint_style=ft.TextStyle(
                color=ft.Colors.with_opacity(0.5, ft.Colors.ON_SURFACE), size=13
            ),
            height=32,  # Hard-locked compact dimension profile
            text_size=13,  # Scaled down to prevent text vertical wrapping
            text_vertical_align=ft.VerticalAlignment.CENTER,
            on_change=self.on_search_change,
            on_submit=self.on_submit,
            # Material 3 Styling mapping to your exact Theme values
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            color=ft.Colors.ON_SURFACE,
            border_radius=10,  # Matches every other input in the app (form/input.py etc.)
            # Low opacity state-layer boundaries matching your architectural commentary
            border_color=ft.Colors.OUTLINE_VARIANT,
            focused_border_color=ft.Colors.TERTIARY,
            # Content padding adjustment prevents the text block from drifting out of alignment
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            # `prefix_icon`/`suffix_icon` (not `prefix`/`suffix`) - Flutter's
            # InputDecoration only renders `prefix`/`suffix` once the field is
            # focused or non-empty; `prefix_icon`/`suffix_icon` render
            # unconditionally, which is what a persistent search/clear icon
            # needs (issue #19). `input.py`'s `prefix_icon` usage never had
            # this bug for the same reason.
            prefix_icon=ft.Icon(ft.Icons.SEARCH, color=ft.Colors.ON_SURFACE, size=14),
            suffix_icon=suffix_control,
            # Without this, Flutter reserves its default ~48dp tap-target
            # width/height for the suffix icon slot, pushing it well past the
            # field's true right edge - the "clear icon sits too far right"
            # regression from issue #19. Width tracks the real content (one
            # icon, or two when the scan button is enabled).
            suffix_icon_size_constraints=ft.BoxConstraints(
                min_width=suffix_width,
                max_width=suffix_width,
                min_height=24,
                max_height=24,
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

    def _apply_scanned_code(self, code: str) -> None:
        """Put a scanned code into the search box and filter the table (#52).

        Deliberately a plain search rather than an option lookup: this bar
        filters rows server-side via `table-keyword-filter`, so a scanned
        location code narrows the table exactly as typing it would - no
        option list exists here to resolve against.
        """
        self.search_bar.value = code
        self._safe_update()
        self.storage.table_search.set(
            self.parent.module, self.parent.screen, self.parent.name, code
        )
        if self.on_filter_change:
            self.on_filter_change(code.lower())

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
