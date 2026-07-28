import flet as ft
from components.table.columns import TABLE_COLUMN_SPACING, TABLE_HORIZONTAL_MARGIN, TableColumns
from components.table.rows import TableRows


class TableBody:
    def __init__(self, page: ft.Page, columns: TableColumns, rows: TableRows, on_scroll_end=None):
        self.page = page
        self.columns = columns
        self.rows = rows
        self.data_table: ft.DataTable | None = None
        self.scrollable_table: ft.Column | None = None
        self.body_container: ft.Container | None = None
        self.loading_indicator: ft.ProgressRing | None = None
        self.loading_overlay: ft.Container | None = None
        self.on_scroll_end = on_scroll_end
        self.is_loading = False
        self.last_scroll_position = 0

    def build(self):
        self.data_table = ft.DataTable(
            # interactive=False: this DataTable's heading row exists purely
            # for structural column-width alignment and is hidden
            # (heading_row_height=0 below) - the real, visible header lives
            # in TableHeader. A sort icon built into this hidden row could
            # visually bleed into the first data row (Flutter's DataTable
            # doesn't fully clip a zero-height heading row's content), so
            # this row never gets sort icons/on_sort handlers at all.
            columns=self.columns.build(interactive=False),
            rows=self.rows.build(),
            column_spacing=TABLE_COLUMN_SPACING,
            horizontal_margin=TABLE_HORIZONTAL_MARGIN,
            heading_row_height=0,  # Hide header
            # No border/row-divider lines (issue #57) - replaced by
            # TableRows.load()'s position-based zebra striping, which reads
            # more cleanly row-to-row than a boxed grid with divider lines.
            # `divider_thickness=0` is the actual fix for the horizontal
            # lines Flutter's DataTable draws between rows by default (1.0)
            # - border alone only ever controlled the table's own outer
            # frame, never those per-row dividers.
            border=None,
            divider_thickness=0,
            # Material 3's own DataTable default is 52dp per data row -
            # this is already a step tighter ("dense" density) since our
            # cell content is always single-line text/inputs, never
            # needing that much vertical room.
            data_row_min_height=36,
            data_row_max_height=44,
        )

        # Wrap DataTable in a scrollable Column
        self.scrollable_table = ft.Column(
            controls=[self.data_table],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            on_scroll=self._on_scroll,
        )

        # Loading indicator overlay
        self.loading_indicator = ft.ProgressRing(visible=False)
        self.loading_overlay = ft.Container(
            content=ft.Column(
                controls=[self.loading_indicator, ft.Text("Loading...", visible=False)],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment.CENTER,
            visible=False,
            expand=True,
        )

        self.body_container = ft.Container(
            content=ft.Stack(controls=[self.scrollable_table, self.loading_overlay]),
            expand=True,
        )
        return self.body_container

    def _on_scroll(self, e: ft.OnScrollEvent):
        """Detect when user scrolls near bottom.

        The `max_scroll_extent <= 0` case (content doesn't overflow the
        viewport yet) is handled defensively here too, but this is NOT the
        real fix for "a short/tall-viewport page can't load the rest of
        its data" - confirmed empirically that Flet's `on_scroll` never
        fires at all in that situation (no overflow means no scroll
        gesture, so no event, so this method is never even called). The
        actual fix is `Table._should_eagerly_load_more()`, a page-height
        heuristic that runs independently of any scroll event."""
        # Save scroll position
        self.last_scroll_position = e.pixels

        if self.is_loading or self.on_scroll_end is None:
            return

        if e.max_scroll_extent is None:
            return

        if e.max_scroll_extent <= 0:
            print("No scroll extent yet - eagerly checking for more data...")
            self.is_loading = True
            self.on_scroll_end()
            self.is_loading = False
            return

        # Load more when scrolled to 90% or more
        scroll_percentage = e.pixels / e.max_scroll_extent

        if scroll_percentage >= 0.9:
            print(f"Scroll triggered: {scroll_percentage:.2%} - Loading more...")
            self.is_loading = True
            self.on_scroll_end()
            self.is_loading = False

    def restore_scroll_position(self) -> None:
        """Re-apply the scroll offset the user was at before this body's
        controls were rebuilt (issue: a lazy-load-more append used to jump
        back to the top, since Table.load() swaps in a brand new
        ft.Column/DataTable rather than mutating the existing one - a
        freshly created scrollable control always starts at offset 0
        client-side, even though this TableBody Python instance (and its
        `last_scroll_position`) persists across rebuilds). Only meaningful
        after an append (more rows added below what's already visible) -
        a fresh, non-append load (filter/sort change) should stay at the
        top, so callers only invoke this for the append case."""
        if self.scrollable_table is not None and self.last_scroll_position > 0:
            try:
                self.page.run_task(
                    self.scrollable_table.scroll_to,
                    offset=self.last_scroll_position, duration=0
                )
            except Exception as e:
                print(f"Could not restore scroll position: {e}")

    def update(self):
        print("TableBody.update")
        print(self.columns.widths)
        if self.data_table is not None:
            self.data_table.columns = self.columns.build(interactive=False)
            self.data_table.rows = self.rows.rows
            self.data_table.update()
            print("data_table updated")
            self.restore_scroll_position()

    def show_loading(self):
        """Show loading indicator"""
        if self.loading_overlay is not None:
            self.loading_overlay.visible = True
            self.loading_indicator.visible = True
            if self.body_container is not None:
                self.body_container.update()

    def hide_loading(self):
        """Hide loading indicator"""
        if self.loading_overlay is not None:
            self.loading_overlay.visible = False
            self.loading_indicator.visible = False
            if self.body_container is not None:
                self.body_container.update()
