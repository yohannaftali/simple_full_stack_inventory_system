"""Shared transactional bulk-create helper for `POST C_{module}/submit_bulk`
endpoints (issue #5) - ALL OR NOTHING: either every uploaded row is created
or none are.

Per-table repositories each open their own `SessionLocal()` block, so they
cannot share one transaction - like `inventory_service.py` (the precedent
for multi-write atomicity in this codebase), this module owns a single
session for the whole batch. Each router supplies a `build_instance(row,
session)` callable that validates one parsed row and returns an unpersisted
model instance, raising `BulkRowError` with the same message its module's
single-record `submit` would have produced; `bulk_create` adds + flushes
row by row (a flush surfaces unique-constraint violations - both in-file
duplicates and conflicts with existing rows - attributed to the row that
caused them) and commits only once at the end. Any failure rolls the whole
batch back.

Wire format (mirrors `C_stock_out/submit_items`): repeated form fields, one
value per row per field, plus a parallel `row_number` list carrying the
uploaded file's own row numbering so error messages point at the row the
user can actually see in their spreadsheet.
"""

from sqlalchemy.exc import IntegrityError

from models.base import SessionLocal


class BulkRowError(Exception):
    """One row failed validation - aborts (rolls back) the whole batch."""

    def __init__(self, row_number: str, message: str):
        super().__init__(message)
        self.row_number = row_number
        self.message = message


def parse_bulk_rows(form, field_names: list[str]) -> list[dict]:
    """Zip repeated form fields into one dict per row.

    `row_number` (sent by the frontend, the file's own numbering) drives
    the row count; a field the file didn't carry simply yields "" for
    every row, leaving required-field validation to `build_instance`.
    Each row dict carries its file row number under `_row`.
    """
    row_numbers = form.getlist("row_number")
    lists = {name: form.getlist(name) for name in field_names}
    rows = []
    for i, row_number in enumerate(row_numbers):
        row = {"_row": str(row_number)}
        for name, values in lists.items():
            row[name] = values[i] if i < len(values) else ""
        rows.append(row)
    return rows


def bulk_create(rows: list[dict], build_instance) -> dict:
    """Create every row in ONE transaction; first failure rolls back all.

    Returns `{"message": "N records created"}` or `{"error": "Row N: ..."}`
    - the same body-shape contract as every other submit endpoint.
    """
    if not rows:
        return {"error": "No rows to import"}

    with SessionLocal() as session:
        current_row = rows[0]["_row"]
        try:
            for row in rows:
                current_row = row["_row"]
                instance = build_instance(row, session)
                session.add(instance)
                # Flush (not commit): surfaces unique-constraint violations
                # now, attributed to this row, while keeping everything in
                # the one uncommitted transaction.
                session.flush()
            session.commit()
        except BulkRowError as e:
            session.rollback()
            return {"error": f"Row {e.row_number}: {e.message}"}
        except IntegrityError:
            session.rollback()
            return {
                "error": (
                    f"Row {current_row}: duplicate value or invalid reference "
                    "(already exists in the database or earlier in this file)"
                )
            }

    return {"message": f"{len(rows)} records created"}
