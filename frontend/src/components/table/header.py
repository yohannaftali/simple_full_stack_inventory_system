import flet as ft
from components.table.columns import Columns


class Header:
    def __init__(self, page: ft.Page, columns: Columns):
        self.page = page
        self.columns = columns
        self.data_table: ft.DataTable | None = None

    def build(self):
        self.data_table = ft.DataTable(
            columns=self.columns.build(),
            rows=[],
            column_spacing=5,
            heading_row_color=ft.Colors.SECONDARY_CONTAINER,
            horizontal_margin=10,
            border=ft.Border.only(
                left=ft.BorderSide(1, ft.Colors.OUTLINE),
                right=ft.BorderSide(1, ft.Colors.OUTLINE),
                top=ft.BorderSide(1, ft.Colors.OUTLINE),
            ),
            data_row_min_height=40,
        )
        return self.data_table

    def update(self):
        print("Header.update")
        print(self.columns.widths)
        if self.data_table is not None:
            self.data_table.columns = self.columns.columns
            self.data_table.update()
            print("data_table updated")
