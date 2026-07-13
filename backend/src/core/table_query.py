"""Reusable pagination / keyword-filter / sort helper for admin-style list
endpoints.

Python port of the pagination/filtering/sort half of the legacy PHP
`L_database` library (`result_rows` / `filter_table_keyword` /
`return_rows_limited` / `sort`), and of `y.form.js`'s
`serializeOrderBy`/`listenerHeaderTable` wire format on the frontend side of
that same original app. SQLAlchemy's query builder already covers the
select/join/where DSL that made up the rest of `L_database`, so only the part
that was actually duplicated across every `list_*` repository method and
every `get_detail` router in this codebase got ported: OR-LIKE keyword search
across columns, resolving page/limit/offset into a single effective offset,
multi-column sort, and shaping the `db_total_page` / `db_num_rows` metadata
that the frontend's `components/table/table.py::get_data()` reads off
`response[0]`.

Every new paginated list endpoint (repository method + router) must use
`apply_keyword_filter` + `apply_sort` + `paginate` + `attach_pagination`
instead of hand-rolling this logic again — see AGENTS.md's "Table
list/pagination convention" section.
"""

import math
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from sqlalchemy import or_
from sqlalchemy.orm import Query


def resolve_offset(page: int, limit: int, offset: int) -> int:
    """`page`+`limit` takes precedence over a raw `offset`, matching
    `L_database::return_rows_limited`'s
    `$offset = $page && $limit ? ($page - 1) * $limit : $get['offset']`."""
    if page and limit:
        return max(page - 1, 0) * limit
    return offset


def apply_keyword_filter(query: Query, columns: Sequence, keyword: str) -> Query:
    """OR-LIKE `keyword` across `columns`. Mirrors the non-aggregate branch of
    `L_database::filter_table_keyword` — this codebase has no aggregate/HAVING
    list screens with a table-keyword-filter yet, so that branch wasn't
    ported; add it here if one shows up."""
    if not keyword or not columns:
        return query
    like = f"%{keyword}%"
    return query.filter(or_(*[column.like(like) for column in columns]))


_SORT_FIELD_PATTERN = re.compile(r"^sort-fields\[(\d+)\]\[(.+)\]$")


def parse_sort_fields(query_params) -> list[tuple[str, str]]:
    """Parse `sort-fields[N][field]=ASC|DESC` query params into an ordered
    `[(field, direction), ...]` list, `N` (the bracketed index) giving each
    entry's sort priority — mirrors `y.form.js`'s `serializeOrderBy()`
    wire format exactly, and `L_database::sort()`'s `ksort($sort)` (order by
    that same index) on the read side. `field` is whatever name the frontend
    field config uses (see `Columns` field dicts' `"name"`), resolved to a
    real column via `apply_sort()`'s `column_map` — not necessarily a raw
    DB column name.

    `query_params` needs a `.multi_items()` (FastAPI/Starlette
    `Request.query_params`) or to already be an iterable of `(key, value)`
    pairs.
    """
    entries: dict[int, tuple[str, str]] = {}
    items = (
        query_params.multi_items()
        if hasattr(query_params, "multi_items")
        else query_params
    )
    for key, value in items:
        match = _SORT_FIELD_PATTERN.match(key)
        if not match:
            continue
        index = int(match.group(1))
        field = match.group(2)
        direction = "DESC" if str(value).upper() == "DESC" else "ASC"
        entries[index] = (field, direction)

    return [entries[i] for i in sorted(entries)]


def apply_sort(
    query: Query, sort_fields: list[tuple[str, str]], column_map: Mapping[str, object]
) -> Query:
    """Apply `ORDER BY` for each `(field, direction)` pair from
    `parse_sort_fields()`, in priority order (multi-column - each additional
    entry is a secondary/tertiary/... sort key, not a replacement) -
    mirrors `L_database::sort()`. `column_map` resolves a field name to the
    real SQLAlchemy column/expression to sort by (same purpose as
    `L_database::normalize_sort_fields()`'s alias map, just always applied
    here rather than being optional); a field with no entry in `column_map`
    is silently skipped rather than raising, matching the PHP's leniency
    (typos or a stale/removed column in the request just don't sort)."""
    if not sort_fields:
        return query
    order_clauses = []
    for field, direction in sort_fields:
        column = column_map.get(field)
        if column is None:
            continue
        order_clauses.append(column.desc() if direction == "DESC" else column.asc())
    if order_clauses:
        query = query.order_by(*order_clauses)
    return query


@dataclass
class Pagination:
    total: int
    limit: int
    offset: int
    page: int

    @property
    def total_pages(self) -> int:
        return max(math.ceil(self.total / self.limit), 1) if self.limit else 1

    def to_meta(self) -> dict:
        """Field names match `L_database::return_rows_limited`'s `$r[0][...]`
        keys, which `components/table/table.py::get_data()` reads off
        `response[0]`."""
        return {
            "db_num_rows": self.total,
            "db_offset": self.offset,
            "db_limit": self.limit,
            "db_page": self.page,
            "db_total_page": self.total_pages,
        }


def paginate(
    query: Query, limit: int, page: int = 1, offset: int = 0
) -> tuple[list, Pagination]:
    """Count + offset/limit a query in one call. Returns (rows, Pagination).

    Uses `query.count()` (not a manual `func.count(some_column)`) so this
    works uniformly for both plain queries and grouped/aggregate queries
    (e.g. `stock_repository.py` / `usage_report_repository.py`), same as
    `L_database::return_rows_limited`'s `count_all_results`.
    """
    total = query.count()
    effective_offset = resolve_offset(page, limit, offset)
    rows = query.offset(effective_offset).limit(limit).all() if limit else query.all()
    return rows, Pagination(total=total, limit=limit, offset=effective_offset, page=page)


def attach_pagination(rows: list[dict], pagination: Pagination) -> list[dict]:
    """Attach page metadata to the first row only — matches the PHP
    convention (`$r[0][...]`) and is all the frontend actually reads."""
    if rows:
        rows[0].update(pagination.to_meta())
    return rows
