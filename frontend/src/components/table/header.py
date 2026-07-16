import flet as ft
from components.table.columns import TABLE_COLUMN_SPACING, TABLE_HORIZONTAL_MARGIN, TableColumns


class TableHeader:
    def __init__(self, page: ft.Page, columns: TableColumns):
        self.page = page
        self.columns = columns
        self.data_table: ft.DataTable | None = None

    def build(self):
        self.data_table = ft.DataTable(
            columns=self.columns.build(),
            rows=[],
            column_spacing=TABLE_COLUMN_SPACING,
            heading_row_color=ft.Colors.SECONDARY_CONTAINER,
            horizontal_margin=TABLE_HORIZONTAL_MARGIN,
            border=ft.Border.only(
                left=ft.BorderSide(1, ft.Colors.OUTLINE),
                right=ft.BorderSide(1, ft.Colors.OUTLINE),
                top=ft.BorderSide(1, ft.Colors.OUTLINE),
            ),
            # Material 3's own default is 56dp - tightened to match
            # body.py's now-denser data_row_max_height (44) for a
            # consistent look, since our header labels are always
            # single-line (see Columns._build_data_columns()'s
            # overflow=ELLIPSIS/max_lines=1).
            heading_row_height=44,
        )
        return self.data_table

    def update(self):
        print("TableHeader.update")
        print(self.columns.widths)
        if self.data_table is not None:
            self.data_table.columns = self.columns.columns
            self.data_table.update()
            print("data_table updated")
