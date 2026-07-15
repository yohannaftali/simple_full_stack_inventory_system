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


_FIELD_FILTER_OPS = {
    ">=": lambda column, value: column >= value,
    "<=": lambda column, value: column <= value,
    "==": lambda column, value: column == value,
    ">": lambda column, value: column > value,
    "<": lambda column, value: column < value,
    "!=": lambda column, value: column != value,
}


def apply_field_filters(
    query: Query, filters: Sequence[tuple[object, str, object]]
) -> Query:
    """Apply a list of `(column, operator, value)` structured filters,
    skipping any whose `value` is falsy (blank/None) — same "absent means
    no filter" leniency as `apply_keyword_filter`, just for named,
    independently-optional filters (`{field}-filter` query params, e.g.
    `start_date-filter`/`end_date-filter`/`supplier_id-filter`) rather than
    one free-text OR-LIKE search. `operator` is one of `">="`, `"<="`,
    `"=="`. Callers parse each `{field}-filter` query param themselves
    (blank string, or an invalid date, become `None`/falsy before reaching
    here) since — unlike `sort-fields[N][field]`'s dynamic bracket keys —
    these are fixed, named params a router can bind directly via
    `Query("", alias="...")`.

    Not per-endpoint bespoke: any new report screen needing this same
    date-range / single-FK filter shape reuses this helper instead of
    hand-rolling its own `if value: query.filter(...)` chain."""
    for column, operator, value in filters:
        if not value:
            continue
        query = query.filter(_FIELD_FILTER_OPS[operator](column, value))
    return query


_NUMERIC_FILTER_TOKEN = re.compile(r"^(>=|<=|!=|<>|>|<|=)(-?\d+(?:\.\d+)?)$")
_PLAIN_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


def _parse_numeric_filter(param: str) -> list[tuple[str, float]]:
    """Port of senar's `L_database::filter_numeric()`: a bare number means
    an exact match (`==`); otherwise one or more `and`-joined
    `{operator}{number}` segments (e.g. `>=5and<=10` for a range) — a
    *literal substring* split on `"and"`, matching PHP's `explode("and",
    $param)` (not a regex word-boundary split). `operator` is one of `>=`,
    `<=`, `>`, `<`, `=`, `!=`/`<>` (normalized to `==`/`!=` to match
    `_FIELD_FILTER_OPS`'s keys). A segment that doesn't parse as
    `{operator}{number}` is silently skipped, matching the PHP's leniency
    (`count($split_array) == 2` check) rather than raising."""
    param = re.sub(r"\s+", "", param)
    if not param:
        return []
    if _PLAIN_NUMBER.match(param):
        return [("==", float(param))]

    conditions: list[tuple[str, float]] = []
    for segment in param.split("and"):
        match = _NUMERIC_FILTER_TOKEN.match(segment)
        if not match:
            continue
        operator, value = match.group(1), float(match.group(2))
        if operator == "<>":
            operator = "!="
        elif operator == "=":
            operator = "=="
        conditions.append((operator, value))
    return conditions


def apply_column_filters(
    query: Query,
    query_params,
    column_map: Mapping[str, object],
    numeric_fields: Sequence[str] = (),
) -> Query:
    """Per-column `{field}-filter` mechanism ported from senar's
    `L_database::filter()` — every column in `column_map` gets its own
    independently-optional filter: `LIKE '%value%'` by default, or
    operator-syntax (`_parse_numeric_filter`) for any column named in
    `numeric_fields`. Mirrors `filter()`'s own precedence: skipped entirely
    if `table-keyword-filter` is also present (the free-text search and
    the per-column filter row are mutually exclusive on the PHP side, not
    combined) — call `apply_keyword_filter` first and only reach this
    helper when `keyword` was blank, same ordering `apply_sort` already
    expects relative to `apply_keyword_filter`.

    `query_params` needs `.multi_items()` (FastAPI/Starlette
    `Request.query_params`) or a plain iterable of `(key, value)` pairs —
    like `parse_sort_fields()`, a `{field}-filter` name isn't a single,
    individually-declared `Query(...)` param (there's one per filterable
    column, config-driven on the frontend, not enumerable ahead of time on
    the backend), so this reads the raw params directly rather than
    binding each one as its own typed FastAPI parameter.

    No `HAVING`/aggregate-column routing yet (senar's `$having` array) —
    this codebase has no aggregate list screen wired onto this helper yet;
    add that branch here if/when one needs it, same gap already noted on
    `apply_keyword_filter`."""
    items = (
        query_params.multi_items()
        if hasattr(query_params, "multi_items")
        else list(query_params)
    )

    keyword = next((value for key, value in items if key == "table-keyword-filter"), "")
    if keyword:
        return query

    values: dict[str, str] = {}
    for key, value in items:
        if not key.endswith("-filter") or key == "table-keyword-filter":
            continue
        field = key[: -len("-filter")]
        if field in column_map:
            values[field] = value

    numeric_set = set(numeric_fields)
    for field, param in values.items():
        param = (param or "").strip()
        if not param:
            continue
        column = column_map[field]
        if field in numeric_set:
            for operator, value in _parse_numeric_filter(param):
                query = query.filter(_FIELD_FILTER_OPS[operator](column, value))
        else:
            query = query.filter(column.like(f"%{param}%"))
    return query


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
