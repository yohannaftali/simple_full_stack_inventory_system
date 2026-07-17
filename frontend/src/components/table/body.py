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
            border=ft.Border.only(
                left=ft.BorderSide(1, ft.Colors.OUTLINE),
                right=ft.BorderSide(1, ft.Colors.OUTLINE),
                bottom=ft.BorderSide(1, ft.Colors.OUTLINE),
            ),
            border_radius=ft.BorderRadius.only(bottom_left=5, bottom_right=5),
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
        """Detect when user scrolls near bottom"""
        # Save scroll position
        self.last_scroll_position = e.pixels

        if self.is_loading or self.on_scroll_end is None:
            return

        # Check if we have valid scroll extent
        if e.max_scroll_extent is None or e.max_scroll_extent <= 0:
            return

        # Load more when scrolled to 90% or more
        scroll_percentage = (
            e.pixels / e.max_scroll_extent if e.max_scroll_extent > 0 else 0
        )

        if scroll_percentage >= 0.9:
            print(f"Scroll triggered: {scroll_percentage:.2%} - Loading more...")
            self.is_loading = True

    def update(self):
        print("TableBody.update")
        print(self.columns.widths)
        if self.data_table is not None:
            self.data_table.columns = self.columns.build(interactive=False)
            self.data_table.rows = self.rows.rows
            self.data_table.update()
            print("data_table updated")

            # Restore scroll position after update
            if self.scrollable_table is not None and self.last_scroll_position > 0:
                try:
                    self.page.run_task(
                        self.scrollable_table.scroll_to,
                        offset=self.last_scroll_position, duration=0
                    )
                except Exception as e:
                    print(f"Could not restore scroll position: {e}")

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
