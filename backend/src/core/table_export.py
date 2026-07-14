"""Multi-format table export helper, shared by every `GET C_{module}/export`
endpoint (see AGENTS.md's "Table export convention"). Takes the same shape a
router already builds for `get_detail` - a list of row dicts plus a
`[(field, label), ...]` column spec - and renders it as CSV/TSV/SCSV/XLSX/
ODS/PDF, so a router only has to supply its data and column labels, not
reimplement six file formats.
"""

import csv
import io
from typing import Sequence

from fastapi import HTTPException
from fastapi.responses import Response
from openpyxl import Workbook
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table as OdsTable, TableRow, TableCell
from odf.text import P
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table as PdfTable, TableStyle

Column = tuple[str, str]  # (field, label)

_DELIMITERS = {"csv": ",", "tsv": "\t", "scsv": ";"}
_MEDIA_TYPES = {
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "scsv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "pdf": "application/pdf",
}


def _cell_value(row: dict, field: str) -> str:
    value = row.get(field, "")
    return "" if value is None else str(value)


def _build_delimited(rows: list[dict], columns: Sequence[Column], delimiter: str) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([label for _, label in columns])
    for row in rows:
        writer.writerow([_cell_value(row, field) for field, _ in columns])
    return buffer.getvalue().encode("utf-8-sig")


def _build_xlsx(rows: list[dict], columns: Sequence[Column]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([label for _, label in columns])
    for row in rows:
        sheet.append([_cell_value(row, field) for field, _ in columns])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _build_ods(rows: list[dict], columns: Sequence[Column]) -> bytes:
    document = OpenDocumentSpreadsheet()
    table = OdsTable(name="Export")

    header_row = TableRow()
    for _, label in columns:
        cell = TableCell(valuetype="string")
        cell.addElement(P(text=label))
        header_row.addElement(cell)
    table.addElement(header_row)

    for row in rows:
        data_row = TableRow()
        for field, _ in columns:
            cell = TableCell(valuetype="string")
            cell.addElement(P(text=_cell_value(row, field)))
            data_row.addElement(cell)
        table.addElement(data_row)

    document.spreadsheet.addElement(table)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _build_pdf(rows: list[dict], columns: Sequence[Column]) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm
    )
    data = [[label for _, label in columns]]
    for row in rows:
        data.append([_cell_value(row, field) for field, _ in columns])

    table = PdfTable(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    document.build([table])
    return buffer.getvalue()


_BUILDERS = {
    "csv": lambda rows, columns: _build_delimited(rows, columns, _DELIMITERS["csv"]),
    "tsv": lambda rows, columns: _build_delimited(rows, columns, _DELIMITERS["tsv"]),
    "scsv": lambda rows, columns: _build_delimited(rows, columns, _DELIMITERS["scsv"]),
    "xlsx": _build_xlsx,
    "ods": _build_ods,
    "pdf": _build_pdf,
}


def export_response(rows: list[dict], columns: Sequence[Column], format: str, filename_base: str) -> Response:  # noqa: A002
    """Render `rows` (list of dicts) as `format` and return a FastAPI
    `Response` with a `Content-Disposition: attachment` header carrying a
    sensible filename - the frontend's download proxy route
    (`frontend/src/asgi.py`) forwards this header as-is to the browser."""
    builder = _BUILDERS.get(format)
    if builder is None:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")

    content = builder(rows, columns)
    media_type = _MEDIA_TYPES[format]
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.{format}"'},
    )
