import flet as ft

from components.table.columns import Columns


class Rows:
    def __init__(self, page: ft.Page, columns: Columns, parent=None):
        self.page = page
        self.columns = columns
        self.parent = parent
        self.rows = []
        self.index = []

    def build(self):
        print("Rows.build")
        print(self.columns.widths)
        return self.rows

    def load(self, data: list, append: bool = False):
        columns_widths: list[int] | None = self.columns.widths
        print("Rows.load: coloumns width")
        print(columns_widths)
        row = len(self.rows) if append else 0
        if not append:
            self.rows = []
            self.index = []
        # determine key field name (field with 'key': True)
        key_field = None
        try:
            for f in getattr(self.columns, 'fields', []):
                if f.get('key'):
                    key_field = f.get('name')
                    break
        except Exception:
            key_field = None
        for record in data:
            # determine key value for this row (if key_field defined)
            key_value = record.get(key_field) if key_field is not None else None

            # create on_tap handler to navigate to edit page with key
            on_tap_handler = None
            if key_field is not None:
                module = None
                if hasattr(self, 'parent') and getattr(self.parent, 'module', None):
                    module = getattr(self.parent, 'module')
                elif hasattr(self.page, 'data') and isinstance(self.page.data, dict):
                    module = self.page.data.get('module')

                if module:
                    def _make_tap(kf, kv, mod):
                        # Use path parameter for id: /modules/<module>/edit/<id>
                        if kv is None:
                            return lambda e: None
                        return lambda e: self.page.run_task(self.page.push_route, f"/modules/{mod}/edit/{kv}")

                    on_tap_handler = _make_tap(key_field, key_value, module)

            cells = []
            for i, name in enumerate(self.columns.index):
                value = record.get(name, "")
                # Wrap text in container with fixed width if available
                content = ft.Text(str(value), overflow=ft.TextOverflow.ELLIPSIS)
                if columns_widths is not None and i < len(columns_widths):
                    # Ensure integer pixel widths (Flet expects integers)
                    w = int(columns_widths[i])
                    content = ft.Container(
                        content=ft.Text(str(value), overflow=ft.TextOverflow.ELLIPSIS),
                        width=w,
                        padding=5,
                    )

                # attach on_tap to each DataCell so clicking any cell navigates
                if on_tap_handler is not None:
                    cell = ft.DataCell(content=content, on_tap=on_tap_handler)
                else:
                    cell = ft.DataCell(content=content)

                cells.append(cell)

            self.rows.append(ft.DataRow(cells=cells))
            self.index.append(row)
            row += 1
