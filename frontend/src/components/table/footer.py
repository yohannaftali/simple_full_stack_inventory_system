"""Sticky table footer (issue #30): a row-count message plus a toggle
between the table's existing infinite lazy-load mode and a classic
numbered-pagination mode, ported from senar's `y.panel.js`/`y.form.js`
footer (`#createRecordInfoPanel()`/`createPaginationButtonSet()`/
`updateTableInfoMessage()`/`listenerPagination()`).

One row on a normal-width screen (issue #37) - the totals message
("Record X-Y of Z") left-aligned, the mode toggle + pagination controls
right-aligned, `SPACE_BETWEEN` in between - wrapping to the original
two-row layout only below `_NARROW_WIDTH_BREAKPOINT`, where the combined
row would otherwise get too cramped:
  - Row 1: the totals message, sourced from the same `db_num_rows`/
    `db_total_page` metadata `Table.get_data()` already reads off
    `response[0]` - no new plumbing, just a new consumer.
  - Row 2 (or the right half of the single combined row): the mode
    toggle, plus (in pagination mode) the pagination controls themselves -
    rows-per-page input, first/prev/numbered-with-ellipsis/next/last
    buttons, current page highlighted. The toggle button is always the
    rightmost control (`_row2_controls()` appends it last) - it used to be
    built first, sitting to the *left* of the pagination buttons instead
    of at the row's true right edge.

Mode state (`self.mode`) is session-only, in-memory on this `TableFooter`
instance - never persisted (confirmed with the user via /planner), same
lifetime as `TableColumns.sort_order`: it resets whenever the owning
`Table` is torn down and rebuilt (e.g. navigating away and back). **Default
is lazy-load** - the pre-existing, only behavior before this issue - so no
table's default look/behavior changes until a user explicitly toggles it.
"""

import flet as ft

from components.button import Button

# Matches y.panel.js's own visible-button cap (max 7, with "..." gap
# markers once the page count exceeds it) - see _page_number_tokens().
_MAX_VISIBLE_PAGE_BUTTONS = 7

# Below this page width, the combined single-row layout (message left,
# controls right) wraps back to the original two stacked rows instead -
# a full set of pagination buttons plus the rows-per-page input doesn't
# comfortably share a row with the message text on a narrow/mobile
# screen. Matches this app's existing informal mobile-ish breakpoint
# (see purchase_report/index.py's ResponsiveRow `col={"sm": 12, "md": 6}`
# - Flet/Bootstrap's own `sm` cutoff is 576px, rounded up here to 600).
_NARROW_WIDTH_BREAKPOINT = 600

MODE_LAZY = "lazy"
MODE_PAGINATION = "pagination"


def _page_number_tokens(current: int, total: int) -> list[int | None]:
    """Page numbers to render as buttons, `None` standing in for a "..."
    gap marker - always keeps the first page, the last page, and a small
    window around `current`, matching y.panel.js's own edge+neighbor
    windowing rather than a plain sliding window (which would hide the
    first/last page entirely on a long list)."""
    if total <= _MAX_VISIBLE_PAGE_BUTTONS:
        return list(range(1, total + 1))

    keep = {1, total, current}
    for p in (current - 1, current + 1):
        if 1 <= p <= total:
            keep.add(p)

    ordered = sorted(keep)
    tokens: list[int | None] = []
    prev = None
    for page in ordered:
        if prev is not None and page - prev > 1:
            tokens.append(None)
        tokens.append(page)
        prev = page
    return tokens


class TableFooter:
    def __init__(self, page: ft.Page, parent):
        """
        Args:
            page: The Flet page.
            parent (Table): the owning Table instance - read live
                (`parent.total_rows`/`parent.total_pages`/`parent.page_number`/
                `parent.limit`/`parent.data`) at every build() call rather
                than cached, since those fields change on every fetch.
        """
        self.page = page
        self.parent = parent
        self.mode = MODE_LAZY

    def build(self) -> ft.Control:
        info_text = ft.Text(
            self._info_message(),
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        controls_row = ft.Row(
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=self._row2_controls(),
        )

        is_narrow = (self.page.width or 0) < _NARROW_WIDTH_BREAKPOINT
        content = (
            ft.Column(spacing=4, controls=[info_text, controls_row])
            if is_narrow
            else ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[info_text, controls_row],
            )
        )

        return ft.Container(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.only(top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            content=content,
        )

    def _info_message(self) -> str:
        total = self.parent.total_rows
        if self.mode == MODE_PAGINATION:
            limit = self.parent.limit or total or 1
            start = (self.parent.page_number - 1) * limit
            shown = len(self.parent.data)
        else:
            start = 0
            shown = len(self.parent.data)
        if total <= 0:
            return "No records"
        first = start + 1
        last = start + shown
        return f"Record {first} - {last} of {total}"

    def _row2_controls(self) -> list:
        # Toggle button always last (rightmost, issue #37) - it used to be
        # built first, landing to the left of the pagination buttons
        # instead of at the row's true right edge.
        controls = []
        if self.mode == MODE_PAGINATION:
            controls.extend(self._build_pagination_controls())
        controls.append(self._build_toggle_button())
        return controls

    def _build_toggle_button(self) -> ft.Control:
        to_pagination = self.mode == MODE_LAZY
        return Button(
            icon=ft.Icons.VIEW_LIST if to_pagination else ft.Icons.ALL_INCLUSIVE,
            tooltip="Switch to pagination" if to_pagination else "Switch to lazy load",
            on_click=self._on_toggle_mode,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            size=32,
            radius=16,
        ).build()

    def _on_toggle_mode(self, e) -> None:
        self.mode = MODE_PAGINATION if self.mode == MODE_LAZY else MODE_LAZY
        self.parent._handle_footer_mode_change(self.mode)

    def _build_pagination_controls(self) -> list:
        total_pages = max(self.parent.total_pages, 1)
        current = min(max(self.parent.page_number, 1), total_pages)

        controls: list = [self._build_limit_input()]

        controls.append(
            self._nav_button(
                ft.Icons.FIRST_PAGE, 1, disabled=current <= 1, tooltip="First page"
            )
        )
        controls.append(
            self._nav_button(
                ft.Icons.CHEVRON_LEFT,
                current - 1,
                disabled=current <= 1,
                tooltip="Previous page",
            )
        )

        for token in _page_number_tokens(current, total_pages):
            if token is None:
                controls.append(
                    ft.Container(
                        content=ft.Text("...", size=12),
                        padding=ft.Padding.symmetric(horizontal=4),
                    )
                )
            else:
                controls.append(self._page_button(token, active=token == current))

        controls.append(
            self._nav_button(
                ft.Icons.CHEVRON_RIGHT,
                current + 1,
                disabled=current >= total_pages,
                tooltip="Next page",
            )
        )
        controls.append(
            self._nav_button(
                ft.Icons.LAST_PAGE,
                total_pages,
                disabled=current >= total_pages,
                tooltip="Last page",
            )
        )
        return controls

    def _nav_button(
        self, icon: str, target_page: int, disabled: bool, tooltip: str
    ) -> ft.Control:
        button = Button(
            icon=icon,
            tooltip=tooltip,
            on_click=(lambda e, p=target_page: self._on_page_click(p)),
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            size=32,
            radius=16,
        ).build()
        button.disabled = disabled
        return button

    def _page_button(self, page_no: int, active: bool) -> ft.Control:
        return ft.Container(
            width=32,
            height=32,
            alignment=ft.Alignment.CENTER,
            border_radius=16,
            bgcolor=ft.Colors.PRIMARY if active else None,
            on_click=None if active else (lambda e, p=page_no: self._on_page_click(p)),
            content=ft.Text(
                str(page_no),
                size=12,
                color=ft.Colors.ON_PRIMARY if active else ft.Colors.ON_SURFACE_VARIANT,
                weight=ft.FontWeight.W_600 if active else ft.FontWeight.NORMAL,
            ),
        )

    def _build_limit_input(self) -> ft.Control:
        return ft.TextField(
            value=str(self.parent.limit),
            width=64,
            height=36,
            text_size=12,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._on_limit_commit,
            on_blur=self._on_limit_commit,
            # Must be set explicitly (issue #35) - a bare ft.TextField's
            # text color isn't theme-aware, same gap as every other
            # TextField in components/table/.
            color=ft.Colors.ON_SURFACE,
            border_color=ft.Colors.OUTLINE_VARIANT,
        )

    def _on_page_click(self, page_no: int) -> None:
        total_pages = max(self.parent.total_pages, 1)
        page_no = min(max(page_no, 1), total_pages)
        if page_no == self.parent.page_number:
            return
        self.parent._handle_footer_page_change(page_no)

    def _on_limit_commit(self, e) -> None:
        raw = (e.control.value or "").strip()
        try:
            new_limit = int(raw)
        except ValueError:
            new_limit = self.parent.limit
        new_limit = max(new_limit, 1)
        if new_limit == self.parent.limit:
            return
        self.parent._handle_footer_limit_change(new_limit)
