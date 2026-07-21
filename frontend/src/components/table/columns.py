import flet as ft

# A rigid-width control (TextField/Dropdown/etc.) has a real rendering
# floor below which Flutter overflows it past its Container - unlike a
# plain Text cell, which just ellipsizes gracefully at any width. The old
# single `min_width = 40` applied to every column let the proportional
# scale-down in _get_widths() squeeze an editable column below that floor.
# Keyed by field "type"; a field-level `"min_width"` always wins over this.
_EDITABLE_MIN_WIDTHS = {
    "checkbox": 50,
    "input": 100,
    "select": 120,
    "option": 120,
    "datepicker": 130,
    "textarea": 160,
    # Wide enough for two 28px compact header buttons side by side
    # (select-all/select-none, or execute-bulk/cancel - see
    # components/table/remove.py's module docstring for why this is two
    # always-visible buttons per mode rather than one Shift-click toggle).
    "remove": 80,
}
_DEFAULT_MIN_WIDTH = 40

# Below this column width, a header label is dropped entirely instead of
# rendered as one unreadable truncated character - see
# Columns._build_data_columns().
_MIN_LABEL_VISIBLE_WIDTH = 24


# Width reserved in a sortable column's label Container for its sort-state
# icon (see _build_sort_icon()) - a real control we build and lay out
# ourselves (unlike the earlier, wrong guess about a phantom Flutter-drawn
# sort icon - see AGENTS.md), so accounting for it here is exact, not an
# approximation.
_SORT_ICON_WIDTH = 20

# Excel/Sheets-style resize handle geometry: a wide but invisible hit
# zone (_RESIZE_HANDLE_HIT_WIDTH) so the user doesn't need pixel-perfect
# aim, centered on the column boundary, with only a thin line
# (_RESIZE_HANDLE_VISIBLE_WIDTH) actually drawn inside it (colored on
# hover/drag - see _build_resize_handle()).
_RESIZE_HANDLE_HIT_WIDTH = 16
_RESIZE_HANDLE_VISIBLE_WIDTH = 2

# Must match the `horizontal_margin`/`column_spacing` components/table/
# header.py and body.py actually construct their DataTables with - used
# to convert a column's content width into the pixel offset where its
# resize handle should sit in the overlay Stack (see
# Columns._reposition_handles()). Centralized here so the two DataTables
# and the handle positioning math can't silently drift apart.
TABLE_HORIZONTAL_MARGIN = 10
TABLE_COLUMN_SPACING = 5

# Must match Table.build()'s own default `padding` (issue #27) - the outer
# Container wrapping header+body is now padded left/right by default instead
# of sitting flush against the screen edge, which shrinks the actual
# available rendering width by this much on each side. get_usable_width()
# below must subtract it from the budget it hands out to columns, or the
# column widths it computes overflow the real (now-narrower) visible area -
# with no horizontal scroll, an overflowing rightmost column simply renders
# off-screen instead of clipping visibly.
TABLE_OUTER_HORIZONTAL_PADDING = 12


class TableColumns:
    def __init__(self, page: ft.Page, fields: list):
        self.page = page
        self.fields = fields
        self.fields_by_name = {
            f.get("name"): f for f in fields if f.get("name") is not None
        }
        self.columns: list = []
        self.index = []
        self.widths: list[int] | None = None
        self.record_key = "id"
        # Set by Table.__init__ when on_remove_row/on_remove_rows is passed
        # (issue #42) - lets _build_data_columns() swap in the remove
        # column's real header button instead of a plain label/sort cell.
        self.remove = None
        # Set once a user drags a resize handle - load() then keeps the
        # current widths on later data reloads (pagination/filter/scroll)
        # instead of recomputing them from content, same as a spreadsheet
        # remembering a manually-set column width.
        self.manually_resized = False
        # Notified after every resize step (Callable[[bool], None], arg =
        # whether to recompute widths from content first) - Table wires it
        # to `Table._handle_resize_commit`. `False` from handle_drag()
        # (every drag tick, current widths kept), `True` from a
        # double-tap reset (Columns.reset_column_pair()).
        #
        # This rebuilds the header/body DataTables with fresh
        # DataColumn/DataCell objects on every step, not just a live
        # `Container.width` patch: Flutter's DataTable grows to fit a
        # wider child during normal layout, but doesn't shrink a column's
        # rendered width back down from a property patch alone - only a
        # rebuild forces that. Doing this on every tick is only safe
        # because the resize handles themselves live *outside* the
        # DataTable entirely now (see get_resize_overlay()) - rebuilding
        # the table never touches the GestureDetector doing the dragging,
        # unlike an earlier version that embedded the handle inside the
        # header's own DataColumn label and broke the drag after the
        # first tick by tearing itself down.
        self.on_resize_commit = None
        # The resize-handle overlay is built once and cached (see
        # get_resize_overlay()) - the caller (Table) re-inserts these same
        # GestureDetector objects into a fresh Stack on every rebuild;
        # Flet's control-id-based patching (not tree-position-based)
        # recognizes they're unchanged and leaves them mounted, preserving
        # any in-progress gesture even though their Stack sibling (the
        # DataTable) is a brand new object each time.
        self._resize_overlay: list[ft.Control] | None = None
        self._handle_controls: dict[int, ft.GestureDetector] = {}
        # Column index currently being dragged, and the pointer's last
        # known global-x - see get_resize_overlay(). Delta is computed
        # manually (diffing consecutive positions) instead of trusting
        # DragUpdateEvent.local_delta/global_delta, which in this Flet
        # build reports values too small to be usable directly.
        self._drag_index: int | None = None
        self._drag_last_x: float | None = None
        # Multi-column sort state: an ordered `[(field_name, "ASC"|"DESC"),
        # ...]` list, list order = sort priority (first entry is the
        # primary sort key) - mirrors the senar reference's
        # `this.orderBy[table]` array (y.form.js). Only fields whose config
        # sets `"sort": True` participate - see on_sort()/
        # _build_data_columns().
        self.sort_order: list[tuple[str, str]] = []
        # Notified after every sort-state change (Callable[[], None]) -
        # Table wires it to `Table._handle_sort_change`, which re-fetches
        # data with the new sort-fields query params (see serialize_sort())
        # - sorting is server-side, unlike the resize handle's purely
        # visual state.
        self.on_sort_change = None
        self.parse_field(self.fields)

    def build(self, interactive: bool = True) -> list:
        # Build and return a FRESH list of DataColumn objects each call.
        # This avoids shared-list aliasing between header/body consumers
        # while keeping `self.widths` as the source-of-truth for sizes.
        # `interactive=False` (used by TableBody, whose DataTable exists
        # purely for structural column-width alignment - its heading row is
        # hidden via heading_row_height=0) strips every sort icon/on_sort
        # handler: Flutter's DataTable doesn't fully clip a zero-height
        # heading row's content, so a real sort icon there could visually
        # bleed into the first data row. The body's own header row is never
        # shown, so it never needs to be interactive in the first place.
        return self._build_data_columns(interactive=interactive)

    def parse_field(self, fields) -> None:
        self.columns = []
        self.index = []

        for field in fields:
            field_name = field.get("name")
            if field_name is None:
                continue

            field_is_key = field.get("key", False)
            if field_is_key:
                self.record_key = field_name

            field_type = field.get("type", "text")
            if field_type == "hidden":
                continue

            field_label = field.get("label")
            field_icon = field.get("icon")

            text = ft.Text(field_label) if field_label is not None else None

            content = None
            if text is not None and field_icon is None:
                content = text
            elif text is not None and field_icon is not None:
                content = ft.Row([field_icon, text])
            elif text is None and field_icon is not None:
                content = field_icon

            self.columns.append(
                ft.DataColumn(label=content, numeric=False, on_sort=None)
            )
            self.index.append(field_name)

    def _on_header_click(self, field_name: str) -> None:
        """Sortable header cell tap - wired directly per-column via
        `Container.on_click` (see _build_data_columns()), NOT
        `DataColumn.on_sort`. Flutter's `DataColumn.onSort` reserves space
        for its own native sort-arrow indicator whenever it's non-null,
        *even though nothing ever paints there* (this table never sets
        `sort_column_index`, and draws its own icon instead) - confirmed via
        Flutter's own API docs. That hidden reservation inflated every
        sortable header cell wider than its `Container(width=w)`, while the
        body's plain DataCell (never given `on_sort`) had no such
        reservation - the actual cause of the header/body column-width
        mismatch that survived three earlier attempts at the icon's own
        layout. Leaving `on_sort` permanently `None` on every `DataColumn`
        (see `parse_field()`/`_build_data_columns()`) removes that
        reservation entirely; this method reproduces the same
        none -> ASC -> DESC -> none cycling `on_sort()` used to do, and a
        *different* column clicked while one is already active still
        appends as an additional sort key rather than replacing - true
        multi-column sort, same as the senar reference's
        `#setOrderByAsc`/`#setOrderByDesc`/`#resetOrderBy` (y.form.js), no
        shift/ctrl modifier needed."""
        index, state = self._find_sort_state(field_name)
        if state == "ASC":
            self.sort_order[index] = (field_name, "DESC")
        elif state == "DESC":
            self.sort_order.pop(index)
        else:
            self.sort_order.append((field_name, "ASC"))

        # Immediate icon feedback, same as the reference toggling the
        # fa-sort* class synchronously before its AJAX call - the actual
        # re-sort still needs a round trip (sorting is server-side), which
        # on_sort_change kicks off separately.
        self.rebuild()
        if self.on_sort_change:
            self.on_sort_change()

    def _find_sort_state(self, field_name: str) -> tuple[int | None, str | None]:
        for i, (name, direction) in enumerate(self.sort_order):
            if name == field_name:
                return i, direction
        return None, None

    def serialize_sort(self) -> str:
        """`&sort-fields[N][field]=ASC|DESC` query string for every active
        sort column, `N` = priority (list order) - exact wire format match
        for `y.form.js`'s `serializeOrderBy()` / `L_database::sort()`'s
        `ksort()`-by-index convention on the backend
        (`backend/src/core/table_query.py::parse_sort_fields()`)."""
        return "".join(
            f"&sort-fields[{index}][{field_name}]={direction}"
            for index, (field_name, direction) in enumerate(self.sort_order)
        )

    def rebuild(self) -> None:
        """Rebuild columns with new widths"""
        self.columns = self._build_data_columns()

    def _build_data_columns(self, interactive: bool = True) -> list:
        print("TableColumns.build (fresh)")
        print(self.widths)
        visible_fields = [
            f
            for f in self.fields
            if f.get("name") is not None and f.get("type", "text") != "hidden"
        ]

        cols: list = []
        for visible_idx, field in enumerate(visible_fields):
            label = field.get("label")
            icon = field.get("icon")
            is_numeric = field.get("is_numeric") or field.get("format") == "number"

            w = (
                int(self.widths[visible_idx])
                if self.widths and visible_idx < len(self.widths)
                else None
            )

            if field.get("type") == "remove":
                # interactive=False is TableBody's own hidden structural
                # header row (heading_row_height=0, see TableBody.build())
                # - Flutter doesn't fully clip a zero-height heading row's
                # content, so a real IconButton there could visually bleed
                # into the first data row, same bug class already fixed for
                # sort icons (see the module docstring's "Fifth round").
                remove_widget = (
                    self.remove.build_header_cell(w)
                    if interactive and self.remove is not None
                    else ft.Container(width=w)
                )
                cols.append(ft.DataColumn(label=remove_widget, numeric=False, on_sort=None))
                continue

            is_sortable = interactive and bool(field.get("sort"))
            # Excel-style: a shrunk column truncates its label to one
            # ellipsized line rather than wrapping onto multiple lines
            # (which used to visibly grow into - "behind" - the row below
            # it). Below _MIN_LABEL_VISIBLE_WIDTH there isn't room for even
            # a truncated word to read as anything, so drop the label
            # entirely rather than show one clipped character. A sortable
            # column's sort icon is NOT gated on this (issue #38) - it has
            # its own reserved width (_min_width_for()'s `_SORT_ICON_WIDTH`
            # addition, independent of the label), and hiding it here used
            # to silently remove the user's only visible way to tell the
            # column was sortable at all, even though the click handler
            # itself (_on_header_click, wired below regardless) still
            # worked - the icon is the only reason a user would ever know
            # to click.
            show_label = label is not None and (
                w is None or w >= _MIN_LABEL_VISIBLE_WIDTH
            )
            text = (
                ft.Text(
                    label,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                    # Must be set explicitly - Flet's DataColumn label Text
                    # doesn't inherit a theme-aware color on its own (issue
                    # #35), and heading_row_color=SECONDARY_CONTAINER
                    # (header.py) needs its "on" contrast color, not
                    # ON_SURFACE.
                    color=ft.Colors.ON_SECONDARY_CONTAINER,
                )
                if show_label
                else None
            )

            row_children = []
            if icon is not None:
                row_children.append(icon)
            if text is not None:
                row_children.append(text)

            if len(row_children) == 0:
                left_content = None
            elif len(row_children) == 1:
                left_content = row_children[0]
            else:
                left_content = ft.Row(row_children, spacing=4, tight=True)

            # Label stays on the left, sort icon pins to the column's right
            # edge. `left_content` is wrapped in an `expand=True` Container
            # so it - not the Row as a whole - is the one given a *bounded*
            # width (Row hands an expand=True child the leftover space after
            # laying out its fixed-size siblings, same as Flutter's own
            # Expanded/Flexible) - this is what makes the label's
            # `overflow=ELLIPSIS` actually take effect. Without it, a Row's
            # non-flex children are laid out with loose (effectively
            # unbounded) width constraints, so a long label's Text never
            # actually gets constrained tightly enough to ellipsize and the
            # whole Row (icon included) can render wider than the outer
            # fixed-width Container - visually bleeding into the next
            # column's header (issue #38 follow-up). The icon itself is
            # fixed-size and always placed last, so it's guaranteed to sit
            # at this column's own right edge, never pushed past it.
            if is_sortable:
                sort_icon = self._build_sort_icon(field["name"])
                if left_content is not None:
                    label_content = ft.Row(
                        [ft.Container(content=left_content, expand=True), sort_icon],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                else:
                    label_content = ft.Row(
                        [sort_icon],
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
            else:
                label_content = left_content

            # Always wrap in a Container - width when available (use
            # integer pixel values; no resize handle attached here anymore,
            # handles live in a separate overlay Stack, see
            # get_resize_overlay()), and unconditionally so a sortable
            # column has somewhere to attach `on_click` even on a first
            # build before widths are computed (plain ft.Row has no
            # on_click of its own).
            final_content = ft.Container(
                content=label_content,
                width=w,
                padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                # Click handling lives here, on the Container, instead of
                # on DataColumn.on_sort - see _on_header_click()'s
                # docstring for why on_sort is never set on any DataColumn
                # in this table anymore (it silently inflates the header
                # cell's rendered width beyond this Container's own
                # explicit `width`, which was the real cause of a
                # persistent header/body column-width mismatch). A column
                # without "sort": True in its field config gets no
                # `on_click` at all, matching the reference's `icon ==
                # null` no-op guard for non-sortable headers.
                on_click=(
                    (lambda e, name=field["name"]: self._on_header_click(name))
                    if is_sortable
                    else None
                ),
            )

            cols.append(
                ft.DataColumn(
                    label=final_content,
                    numeric=is_numeric,
                    on_sort=None,
                )
            )

        return cols

    def _build_sort_icon(self, field_name: str) -> ft.Control:
        """This column's current sort-state indicator - neutral
        (unsorted), or an up/down arrow once it's an active sort key.
        Built ourselves (Flet's DataColumn has no multi-column sort
        indicator of its own - it only ever highlights one
        `sort_column_index`, which this table never sets), same role as
        the reference's `#columnSort()` fa-sort/fa-sort-up/fa-sort-down
        icon."""
        _, direction = self._find_sort_state(field_name)
        if direction == "ASC":
            icon_name, color = ft.Icons.ARROW_UPWARD, ft.Colors.PRIMARY
        elif direction == "DESC":
            icon_name, color = ft.Icons.ARROW_DOWNWARD, ft.Colors.PRIMARY
        else:
            icon_name, color = ft.Icons.UNFOLD_MORE, ft.Colors.ON_SURFACE_VARIANT
        return ft.Icon(icon_name, size=14, color=color)

    def get_resize_overlay(self) -> list[ft.Control]:
        """Positioned resize-handle controls for a Stack wrapping the
        header (`ft.Stack([header_control, *get_resize_overlay()])`) -
        built once and cached; every subsequent call returns the exact
        same control objects so their gesture state/identity survives
        header rebuilds (see on_resize_commit's docstring)."""
        if self._resize_overlay is not None:
            return self._resize_overlay

        num_columns = len(self.index)
        remove_field_name = self._remove_field_name()
        overlay: list[ft.Control] = []
        for i in range(max(num_columns - 1, 0)):
            # No handle on either side of the fixed-width remove column
            # (issue #43) - its width never changes by dragging.
            if remove_field_name is not None and (
                self.index[i] == remove_field_name
                or self.index[i + 1] == remove_field_name
            ):
                continue
            handle = self._build_resize_handle(i)
            self._handle_controls[i] = handle
            overlay.append(handle)

        self._resize_overlay = overlay
        self._reposition_handles()
        return overlay

    def _reposition_handles(self) -> None:
        """Move each resize handle to sit at its column boundary's actual
        rendered x-offset, matching Header/Body's DataTable
        horizontal_margin/column_spacing (TABLE_HORIZONTAL_MARGIN/
        TABLE_COLUMN_SPACING) - called after every width change
        (handle_drag(), load())."""
        if not self.widths or not self._handle_controls:
            return

        cumulative = TABLE_HORIZONTAL_MARGIN
        for i in range(len(self.widths) - 1):
            cumulative += self.widths[i]
            handle = self._handle_controls.get(i)
            if handle is not None:
                handle.left = cumulative - (_RESIZE_HANDLE_HIT_WIDTH / 2)
            cumulative += TABLE_COLUMN_SPACING

        self._safe_page_update()

    def _build_resize_handle(self, index: int) -> ft.GestureDetector:
        """Draggable divider positioned over column `index`'s right edge,
        Excel/Sheets-style manual column resize - a wide but invisible hit
        zone (`_RESIZE_HANDLE_HIT_WIDTH`) so the user doesn't need
        pixel-perfect aim, with only a thin line
        (`_RESIZE_HANDLE_VISIBLE_WIDTH`) actually drawn, centered inside
        it. The line matches the table's own (semantic, theme-aware)
        background color at rest, highlighting to the primary color on
        hover or while actively dragging (hovering/dragging anywhere in
        the wider hit zone counts, not just over the thin line itself).
        Double-tap resets both neighboring columns back to auto-fit."""
        # `expand=True` so the thin line fills the hit zone's full height
        # (set externally via top=0/bottom=0 below), not just its own
        # natural (near-zero) content height.
        bar = ft.Container(
            width=_RESIZE_HANDLE_VISIBLE_WIDTH, bgcolor=ft.Colors.SURFACE, expand=True
        )
        hit_area = ft.Container(
            content=bar,
            width=_RESIZE_HANDLE_HIT_WIDTH,
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.TRANSPARENT,
        )

        def _highlight():
            bar.bgcolor = ft.Colors.PRIMARY
            self._safe_update(bar)

        def _unhighlight():
            bar.bgcolor = ft.Colors.SURFACE
            self._safe_update(bar)

        def _on_enter(e):
            _highlight()

        def _on_exit(e, i=index):
            # Don't unhighlight mid-drag just because a fast pointer
            # movement momentarily left the hit zone - only a real
            # hover-away (no drag in progress) should revert the color.
            if self._drag_index != i:
                _unhighlight()

        def _on_pan_start(e, i=index):
            self._drag_index = i
            self._drag_last_x = e.global_position.x
            _highlight()

        def _on_pan_update(e, i=index):
            if self._drag_index != i or self._drag_last_x is None:
                return
            # Track the pointer's absolute position ourselves and diff
            # consecutive events, rather than trusting
            # DragUpdateEvent.local_delta/global_delta (both reported
            # values too small to be usable).
            current_x = e.global_position.x
            self.handle_drag(i, current_x - self._drag_last_x)
            self._drag_last_x = current_x

        def _on_pan_end(e, i=index):
            if self._drag_index == i:
                self.manually_resized = True
            self._drag_index = None
            self._drag_last_x = None
            _unhighlight()

        def _on_pan_cancel(e, i=index):
            self._drag_index = None
            self._drag_last_x = None
            _unhighlight()

        def _on_double_tap(e, i=index):
            self.reset_column_pair(i)

        return ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.RESIZE_COLUMN,
            # Every tick now triggers a full header/body rebuild (see
            # on_resize_commit's docstring), heavier than the old
            # property-patch-only approach - a lower ~20fps cap keeps
            # that from flooding the connection.
            drag_interval=50,
            top=0,
            bottom=0,
            left=0,
            on_enter=_on_enter,
            on_exit=_on_exit,
            on_pan_start=_on_pan_start,
            on_pan_update=_on_pan_update,
            on_pan_end=_on_pan_end,
            on_pan_cancel=_on_pan_cancel,
            on_double_tap=_on_double_tap,
            content=hit_area,
        )

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except RuntimeError:
            pass

    def _safe_page_update(self) -> None:
        try:
            self.page.update()
        except RuntimeError:
            pass

    def handle_drag(self, index: int, delta_x: float) -> None:
        """Resize column `index` by dragging the handle at its right edge -
        steals/gives width to the next column so the row's total width
        never changes. This table has no horizontal scroll, so a manual
        resize can only redistribute existing space, not grow it; dragging
        the handle left of the last column is the only way to widen it."""
        if not delta_x or not self.widths or index < 0 or index + 1 >= len(self.widths):
            return

        min_w = self._min_width_for(self.index[index])
        min_w_next = self._min_width_for(self.index[index + 1])
        new_w = self.widths[index] + delta_x
        new_w_next = self.widths[index + 1] - delta_x
        if new_w < min_w or new_w_next < min_w_next:
            return

        self.widths[index] = int(new_w)
        self.widths[index + 1] = int(new_w_next)
        self._reposition_handles()
        if self.on_resize_commit:
            self.on_resize_commit(False)

    def reset_column_pair(self, index: int) -> None:
        """Double-tap a resize handle to drop the manual override and let
        the whole table recompute auto-fit widths from content again."""
        self.manually_resized = False
        if self.on_resize_commit:
            self.on_resize_commit(True)

    def get_screen_width(self) -> int:
        # page.width is the actual rendered viewport width on web (and desktop);
        # page.window.width applies to desktop OS windows and is unreliable on
        # web - it was observed returning a small stale default (e.g. 400)
        # while page.width correctly reported the real browser width (e.g.
        # 1653), which made tables render far narrower than the page on web.
        # Prefer page.width whenever it's available; only fall back to
        # window.width (then a hardcoded default) if it isn't.
        if hasattr(self.page, "width") and self.page.width:
            print(f"page.width: {self.page.width}")
            return self.page.width

        if (
            hasattr(self.page, "window")
            and hasattr(self.page.window, "width")
            and self.page.window.width
        ):
            print(f"page.window_width: {self.page.window.width}")
            return self.page.window.width

        return 1200

    def get_usable_width(self, num_columns: int) -> int:
        """Calculate usable width for columns based on page/window size"""
        screen_width = self.get_screen_width()
        print(f"Screen width: {screen_width}")
        horizontal_margin = TABLE_HORIZONTAL_MARGIN
        column_spacing = TABLE_COLUMN_SPACING
        total_spacing = (num_columns - 1) * column_spacing
        # Subtract the DataTable's own horizontal_margin (both sides - real,
        # matches header.py/body.py's own `horizontal_margin=TABLE_HORIZONTAL_MARGIN`)
        # and the Table's outer padding (issue #27 - real, matches
        # Table.build()'s own default). No extra last-column gutter reserved
        # here anymore (removed 2026-07-17 - it stacked with the outer
        # padding and made the right side visibly wider than the left).
        # Also no `scrollbar_width`/`safety_buffer` fudge factors anymore
        # (removed same day) - neither corresponded to a real, always-present
        # rendered element (the body's scrollbar only reserves space when it
        # actually overflows, and `safety_buffer` was `horizontal_margin`
        # applied a *second* time with no distinct purpose), and the toolbar
        # sizes itself with a plain `expand=True` with no equivalent
        # deductions - the extra shrinkage here was exactly what made the
        # header/body's right edge sit visibly short of the toolbar's.
        usable_width = (
            screen_width
            - (horizontal_margin * 2)
            - (TABLE_OUTER_HORIZONTAL_PADDING * 2)
            - total_spacing
        )
        print(f"Usable width: {usable_width}")
        return usable_width

    def _remove_field_name(self) -> str | None:
        """Name of this table's opt-in remove column (issue #42), if any -
        its width is a known constant (room for two compact header
        buttons), never derived from row content."""
        for field in self.fields:
            if field.get("type") == "remove":
                return field.get("name")
        return None

    def load(self, data: list) -> None:
        """Calculate column widths based on content and available screen width"""
        num_columns = len(self.index)
        if num_columns == 0:
            return

        if self.manually_resized and self.widths and len(self.widths) == num_columns:
            # User already fine-tuned column widths by dragging - keep them
            # instead of recomputing from content on every data reload
            # (pagination/filter/scroll-more/page-resize all call this).
            self.rebuild()
            self._reposition_handles()
            return

        usable_width = self.get_usable_width(num_columns)

        # The remove column (issue #43) is fixed-width, not content-driven -
        # reserve its width off the top and size only the remaining columns
        # against what's left, then splice the fixed width back in at its
        # original position. Never included in _get_widths()'s proportional
        # scale-down, so it can neither shrink below nor grow past its
        # known-required width.
        remove_field_name = self._remove_field_name()
        remove_index = (
            self.index.index(remove_field_name)
            if remove_field_name is not None and remove_field_name in self.index
            else None
        )
        if remove_index is not None:
            fixed_remove_width = self._min_width_for(remove_field_name)
            usable_width -= fixed_remove_width
            sizable_fields = [name for name in self.index if name != remove_field_name]
        else:
            fixed_remove_width = None
            sizable_fields = self.index

        min_widths = [self._min_width_for(name) for name in sizable_fields]

        if len(sizable_fields) == 0:
            sizable_widths = []
        elif len(sizable_fields) == 1:
            sizable_widths = [usable_width]
        else:
            sizable_widths = self._get_widths(
                sizable_fields, usable_width, min_widths, data
            )

        widths = [int(w) for w in sizable_widths]
        if remove_index is not None:
            widths.insert(remove_index, int(fixed_remove_width))

        self.widths = widths
        print("TableColumns.load: columns width")
        print(self.widths)
        self.rebuild()
        self._reposition_handles()

    def _min_width_for(self, field_name: str) -> int:
        field = self.fields_by_name.get(field_name, {})
        base = field.get("min_width") or _EDITABLE_MIN_WIDTHS.get(
            field.get("type"), _DEFAULT_MIN_WIDTH
        )
        # A sortable column always renders its own sort-state icon (see
        # _build_sort_icon()) alongside the label - a real control we lay
        # out ourselves, so its width needs accounting for here same as
        # any other content, unlike Flutter's own (never-shown, since this
        # table never sets sort_column_index) built-in sort icon.
        if field.get("sort"):
            base += _SORT_ICON_WIDTH
        # Never narrower than both of a column's resize handles' hit zones
        # (this column's own right-edge handle, plus half of the previous
        # column's, each _RESIZE_HANDLE_HIT_WIDTH wide and centered on the
        # boundary) - otherwise the two would overlap. In practice
        # _DEFAULT_MIN_WIDTH/_EDITABLE_MIN_WIDTHS are already comfortably
        # above this; it's a floor for a field-level `min_width` override
        # small enough to violate it.
        return max(base, _RESIZE_HANDLE_HIT_WIDTH)

    def _get_widths(
        self, field_names: list[str], usable_width, min_widths: list[int], data: list
    ):
        num_columns = len(field_names)
        content_widths, total_content_width = self._get_initial_widths(
            field_names, data, min_widths
        )

        # Adjust widths proportionally if total exceeds usable width
        if total_content_width > usable_width:
            # Scale down proportionally
            prop = usable_width / total_content_width
            widths = [
                max(int(w * prop), min_widths[i]) for i, w in enumerate(content_widths)
            ]

            # Recalculate total after applying each column's own min_width
            total_scaled = sum(widths)
            if total_scaled > usable_width:
                # Apply max constraints more aggressively
                excess = total_scaled - usable_width
                for i, width in enumerate(widths):
                    if excess <= 0:
                        break
                    reduction = min(width - min_widths[i], excess)
                    if reduction > 0:
                        widths[i] -= reduction
                        excess -= reduction
        else:
            # Use content widths as-is
            widths = content_widths
            total_width = sum(widths)
            # Distribute remaining space evenly if we have room
            if total_width < usable_width:
                extra_per_column = (usable_width - total_width) // num_columns
                widths = [w + extra_per_column for w in widths]

        return widths

    def _get_initial_widths(
        self, field_names: list[str], data: list, min_widths: list[int]
    ) -> tuple[list[int], int]:
        # Calculate initial widths based on content
        content_widths: list[int] = []
        total_content_width: int = 0

        for i, field_name in enumerate(field_names):
            # Start with header label length
            field = self.fields_by_name.get(field_name, {})
            header_label = field.get("label", field_name)
            max_length = len(str(header_label))

            # Check all data rows (sample first 20 for performance)
            for record in data[:20]:
                value = str(record.get(field_name, ""))
                max_length = max(max_length, len(value))

            # Convert character length to pixel width
            # Using average character width for typical UI fonts (7-9px at default size)
            # Plus padding for cell spacing (20px each side)
            char_width = 8  # Average width per character in pixels
            cell_padding = 40  # Left + right padding
            width = max(max_length * char_width + cell_padding, min_widths[i])
            content_widths.append(width)
            total_content_width += width

        return content_widths, total_content_width
