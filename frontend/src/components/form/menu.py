"""Hamburger-icon bulk-upload menu for module `new` screens (issue #5).

Attached automatically by `Form.build()` to the far right of the screen's
`ModuleToolbar` whenever `parent.screen == "new"` - no per-module wiring.
Offers "Upload bulk from CSV" / "Upload bulk from XLSX": the file is parsed
client-side (reusing `components/table/menu.py`'s byte parsers, so the same
delimiter sniffing and blank-row skipping apply), headers are matched to
the form's fields by visible label or field name (case-insensitive,
unknown columns ignored), `select` cells are resolved against the field's
option list (by option label or value), and every row is submitted in ONE
`POST C_{module}/submit_bulk` - the backend wraps the batch in a single
transaction, so a failure at any row creates nothing and returns
`Row N: <the same message a manual submit would give>`.

Row numbers count the header as row 1 among the file's non-blank rows
(blank rows are skipped by the parsers and don't consume a number).

Follows the same three Flet invariants documented in AGENTS.md's table
export/upload convention (learned the hard way in #4): page-passive
constructor, FilePicker registered lazily in the async click handler via
`page.services`, and `on_click` handlers that ARE coroutine functions.
"""

import flet as ft

from components.table.menu import parse_csv_bytes, parse_xlsx_bytes
from utils.http_client import HttpClient

# Field types whose columns can be supplied by the uploaded file.
_UPLOADABLE_TYPES = {"input", "date", "select"}


class MenuForm:
    def __init__(self, page: ft.Page, form):
        self.page = page
        self.form = form  # components/form/form.py Form
        self.parent = form.parent  # ModulePage (module, view)
        self.file_picker: ft.FilePicker | None = None

        self.menu = ft.PopupMenuButton(
            icon=ft.Icons.MENU,
            tooltip="Bulk upload",
            height=32,
            width=32,
            style=ft.ButtonStyle(
                padding=0,  # Forces the icon inside the popup boundary to hit absolute center
            ),
            items=[
                ft.PopupMenuItem(
                    content="Upload bulk from CSV",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=self._upload_handler("csv"),
                ),
                ft.PopupMenuItem(
                    content="Upload bulk from XLSX",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=self._upload_handler("xlsx"),
                ),
            ],
        )

    def build(self):
        return self.menu

    def _upload_handler(self, fmt: str):
        async def on_click(e):
            await self._pick_and_submit(fmt)

        return on_click

    async def _pick_and_submit(self, fmt: str):
        if self.file_picker is None:
            self.file_picker = ft.FilePicker()
        if self.file_picker not in self.page.services:
            self.page.services.append(self.file_picker)
            self.page.update()

        allowed = ["csv"] if fmt == "csv" else ["xlsx", "xls"]
        files = await self.file_picker.pick_files(
            allowed_extensions=allowed,
            file_type=ft.FilePickerFileType.CUSTOM,
            with_data=True,
        )
        if not files:
            return

        file_info = files[0]
        data = file_info.bytes
        if data is None and file_info.path:
            try:
                with open(file_info.path, "rb") as f:
                    data = f.read()
            except OSError as ex:
                self._show_error(f"Could not read file: {ex}")
                return
        if data is None:
            self._show_error("Could not read the selected file.")
            return

        try:
            if file_info.name.lower().endswith((".xlsx", ".xls")):
                rows = parse_xlsx_bytes(data)
            else:
                rows = parse_csv_bytes(data)
        except Exception as ex:
            self._show_error(f"Failed to parse {file_info.name}: {ex}")
            return

        if len(rows) < 2:
            self._show_error("The file needs a header row plus at least one data row.")
            return

        payload = self._build_payload(rows)
        if payload is None:
            return  # _build_payload already surfaced the error

        client = HttpClient(self.page)
        response = client.post(f"C_{self.parent.module}/submit_bulk", data=payload)

        if isinstance(response, dict) and "error" in response:
            self._show_error(response["error"])
            return
        message = ""
        if isinstance(response, dict):
            message = str(response.get("message", ""))
        self._show_success(message or "Bulk upload completed.")
        self.page.run_task(self.page.push_route, f"/modules/{self.parent.module}/index")

    def _build_payload(self, rows: list[list[str]]) -> dict | None:
        """File rows -> repeated-form-field payload for submit_bulk.

        Returns None (after surfacing an error) when nothing usable can be
        built - no matching columns, no data rows, or an unresolvable
        select cell (which must abort the whole upload, matching the
        backend's all-or-nothing semantics client-side).
        """
        headers = [str(h).strip() for h in rows[0]]
        data_rows = rows[1:]

        # Header -> form field, by label or name, case-insensitive.
        header_to_field = {}  # file column index -> field dict
        for i, header in enumerate(headers):
            h_norm = header.lower().strip()
            for field in self.form.fields:
                if field.get("type", "input") not in _UPLOADABLE_TYPES:
                    continue
                label = str(field.get("label", ""))
                name = str(field.get("name", ""))
                if label.lower().strip() == h_norm or name.lower().strip() == h_norm:
                    header_to_field[i] = field
                    break

        if not header_to_field:
            self._show_error("No columns in the file matched this form's fields.")
            return None

        # Fetch options once per select field present in the file, resolved
        # from the same endpoint SelectForm itself uses.
        select_options = {}  # field_name -> {normalized label/value: value}
        client = HttpClient(self.page)
        for field in header_to_field.values():
            if field.get("type") != "select":
                continue
            name = field.get("name")
            options = client.get(f"C_{self.parent.module}/call_{name}_select")
            lookup = {}
            if isinstance(options, list):
                for opt in options:
                    value = str(opt.get("value", ""))
                    label = str(opt.get("label", ""))
                    if value:
                        lookup[value.lower().strip()] = value
                    if label:
                        lookup[label.lower().strip()] = value
            select_options[name] = lookup

        lists: dict[str, list[str]] = {
            field.get("name"): [] for field in header_to_field.values()
        }
        row_numbers: list[str] = []

        # Header counts as row 1 among the file's non-blank rows.
        for offset, file_row in enumerate(data_rows, start=2):
            cells = {}
            for file_idx, field in header_to_field.items():
                raw = file_row[file_idx] if file_idx < len(file_row) else ""
                cells[field.get("name")] = str(raw).strip() if raw is not None else ""

            # A row is blank when every matched cell is empty - skip it.
            if not any(cells.values()):
                continue

            for file_idx, field in header_to_field.items():
                name = field.get("name")
                value = cells[name]
                if field.get("type") == "select" and value:
                    resolved = select_options.get(name, {}).get(value.lower())
                    if resolved is None:
                        self._show_error(
                            f"Row {offset}: unknown {field.get('label', name)} '{value}'"
                        )
                        return None
                    value = resolved
                cells[name] = value

            for name in lists:
                lists[name].append(cells.get(name, ""))
            row_numbers.append(str(offset))

        if not row_numbers:
            self._show_error("No data rows found in the file.")
            return None

        payload: dict = {"row_number": row_numbers}
        payload.update(lists)
        return payload

    def _show_error(self, message: str):
        if hasattr(self.parent, "view") and self.parent.view:
            self.parent.view.show_error(message)
        else:
            print(f"Error: {message}")

    def _show_success(self, message: str):
        if hasattr(self.parent, "view") and self.parent.view:
            self.parent.view.show_success(message)
        else:
            print(f"Success: {message}")
