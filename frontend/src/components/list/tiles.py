import flet as ft

from components.list.layout import OVERFLOW_POSITION, Layout
from utils.formatting import format_date, format_datetime, format_number, format_time

# M3 List "Expand & collapse" interaction (issue #81):
# https://m3.material.io/components/lists/guidelines - a list item with
# extra content can expand vertically to reveal it. The spec describes a
# container-transform transition; Flet's Container only exposes a single
# generic `animate` property (implicit animation of whatever properties
# change between renders) with no dedicated "animate to intrinsic/auto
# height" primitive the way Flutter's own AnimatedSize/container-transform
# widgets have, so a smooth grow/shrink of arbitrary extra-field content
# isn't achievable here without a fixed, precomputed height per tile.
# Deliberately using a plain `visible` toggle instead (instant show/hide) -
# a documented, acceptable substitute per this issue's own acceptance
# criteria, not an oversight.
_ICON_COLLAPSED = ft.Icons.EXPAND_MORE
_ICON_EXPANDED = ft.Icons.EXPAND_LESS

# Same "format" dispatch as components/table/rows.py's own _FORMATTERS -
# a "date"/"time"/"datetime"/"number" field value arrives over the wire as a
# raw string (e.g. an ISO date), so a List tile needs the same formatting
# a Table cell already gets, or dates/numbers render unformatted.
_FORMATTERS = {
    "number": format_number,
    "date": format_date,
    "time": format_time,
    "datetime": format_datetime,
}

# Position-based zebra stripe (issue #65, porting Table's own issue #57) -
# derived fresh from each tile's index in the CURRENT render pass (the
# `row` counter below), never stored on the record, so it's automatically
# correct after any full rebuild (search/filter/sort) with no separate
# bookkeeping. Same semantic M3 tokens Table's own TableRows.load() uses,
# for visual consistency between the two components.
_TILE_COLOR_EVEN = ft.Colors.SURFACE
_TILE_COLOR_ODD = ft.Colors.SURFACE_CONTAINER_LOW


class Tiles:
    def __init__(
        self,
        page: ft.Page,
        parent,
        layout: Layout,
        title=None,
        subtitle=None,
        leading=None,
        trailing=None,
        next_page="edit",
    ):
        self.page = page
        self.layout = layout
        self.parent = parent
        self.tiles = []
        self.leading = leading
        self.title = title
        self.subtitle = subtitle
        self.trailing = trailing
        self.next_page = next_page
        self.leading_width = leading.get("width", 80) if leading is not None else 80
        self.trailing_width = trailing.get("width", 80) if trailing is not None else 80
        self.index = []

    def build(self) -> list:
        return self.tiles

    @staticmethod
    def _make_expand_toggle(expand_container: ft.Container, expand_button: ft.IconButton):
        """Per-tile M3 expand/collapse handler - toggles `expand_container`'s
        visibility and the button's own chevron direction. A plain
        `visible` flip (not a height animation) - see this module's own
        top docstring note for why."""

        def _toggle(e):
            expand_container.visible = not expand_container.visible
            expand_button.icon = (
                _ICON_EXPANDED if expand_container.visible else _ICON_COLLAPSED
            )
            expand_button.tooltip = "Show less" if expand_container.visible else "Show more"
            try:
                expand_container.update()
                expand_button.update()
            except RuntimeError:
                pass

        return _toggle

    def load(self, data: list, append: bool = False):
        """Build tiles from data (server handles pagination)

        Args:
            data: List of records to display
            append: If True, append to existing tiles. If False, replace all tiles.
        """
        if not append:
            self.tiles = []
            self.index = []

        # Continues from the last already-rendered tile's index on a
        # lazy-load append (not 0), matching TableRows.load()'s own
        # counter exactly - the stripe pattern doesn't reset/clash at the
        # page boundary. Deliberately named `tile_index`, NOT `row` - this
        # loop body already uses `row` as the per-position row-group index
        # (`for row, row_data in position_data.items()`, Layout's own
        # "row": N grouping within one leading/title/subtitle/trailing
        # slot) - a first attempt named this counter `row` too and got
        # silently shadowed by that inner loop on every iteration, which
        # is why the stripe never appeared (looked identical to a broken
        # ft.ListTile.bgcolor problem at first, until tracing the actual
        # value showed the counter was never advancing per-tile at all).
        tile_index = len(self.tiles) if append else 0

        key_field = self.layout.record_key
        module = None
        if hasattr(self, "parent") and getattr(self.parent, "module", None):
            module = getattr(self.parent, "module")
        elif hasattr(self.page, "data") and isinstance(self.page.data, dict):
            module = self.page.data.get("module")

        def _make_tap(screen: str, value):
            # Shared by both the record-wide tile tap (self.next_page) and
            # any per-field link_key_field/link_screen tap (issue #81) -
            # same `/modules/{module}/{screen}/{value}` shape Table's own
            # `link_key_field` mechanism navigates to.
            if module is None or value is None:
                return None
            return lambda e: self.page.run_task(
                self.page.push_route, f"/modules/{module}/{screen}/{value}"
            )

        for record in data:
            layout = self.layout.layout
            tile_content = {
                "leading": None,
                "title": None,
                "subtitle": None,
                "trailing": None,
            }
            # The overflow ("extra") bucket renders as label:value rows in
            # an M3 expand/collapse section, not through the generic
            # icon+tooltip-value building below (which the fixed
            # leading/title/subtitle/trailing slots all share) - built
            # separately after this loop.
            extra_position_data = layout.get(OVERFLOW_POSITION, {})
            main_layout = {
                position: position_data
                for position, position_data in layout.items()
                if position != OVERFLOW_POSITION
            }

            for position, position_data in main_layout.items():
                position_content = []
                for row, row_data in position_data.items():
                    row_content = []
                    for field_data in row_data:
                        name = field_data.get("name")
                        col = field_data.get("col")
                        label_text = field_data.get("label_text")
                        icon_control = field_data.get("icon_control")
                        value = record.get(name, "")
                        formatter = _FORMATTERS.get(field_data.get("format"))
                        display_value = formatter(value) if formatter and value not in (None, "") else value

                        # The label is a hover tooltip on the value, not a
                        # permanent visible caption line (issue #65
                        # follow-up) - see layout.py's docstring for why
                        # (the same field's "label" is still needed
                        # verbatim by Table's own column header, sharing
                        # one fields list via issue #56's ViewToggle).
                        value_text = ft.Text(
                            str(display_value),
                            overflow=ft.TextOverflow.ELLIPSIS,
                            # `tooltip` is a plain property every Control
                            # has (not a separate wrapping widget) - no
                            # `ft.Tooltip(...)` class exists in this Flet
                            # version.
                            tooltip=label_text if label_text else None,
                        )

                        # Build controls list, filtering out None
                        controls_list = []
                        if icon_control is not None:
                            controls_list.append(icon_control)
                        controls_list.append(value_text)

                        # Wrap text in container with fixed width if available
                        content = ft.Column(controls=controls_list, col=col)

                        # Per-field drill-down link (issue #81) - a nested
                        # clickable Container captures the tap before it
                        # reaches the ListTile's own on_click (same
                        # "inner control wins" behavior already relied on
                        # for the expand chevron above), so a linked field
                        # navigates independently of the tile's own
                        # record-wide tap target.
                        link_key_field = field_data.get("link_key_field")
                        if link_key_field:
                            link_handler = _make_tap(
                                field_data.get("link_screen") or self.next_page,
                                record.get(link_key_field),
                            )
                            if link_handler is not None:
                                content = ft.Container(
                                    content=content,
                                    on_click=link_handler,
                                )

                        row_content.append(content)
                    position_content.append(
                        ft.ResponsiveRow(
                            controls=row_content,
                        )
                    )

                # Wrap position content in Container with constraints
                if position_content:
                    if position == "leading":
                        tile_content[position] = ft.Container(
                            content=ft.Column(controls=position_content, spacing=2),
                            width=self.leading_width,
                            alignment=self.leading.get("alignment")
                            if self.leading is not None
                            else ft.Alignment.CENTER_LEFT,
                        )
                    elif position == "trailing":
                        tile_content[position] = ft.Container(
                            content=ft.Column(controls=position_content, spacing=2),
                            width=self.trailing_width,
                            alignment=self.trailing.get("alignment")
                            if self.trailing is not None
                            else ft.Alignment.CENTER_RIGHT,
                        )
                    elif position == "title":
                        tile_content[position] = ft.Column(
                            controls=position_content,
                            spacing=2,
                            expand=True,
                            alignment=self.title.get(
                                "alignment", ft.Alignment.BOTTOM_CENTER
                            )
                            if self.title is not None
                            else ft.Alignment.BOTTOM_CENTER,
                        )
                    elif position == "subtitle":
                        tile_content[position] = ft.Column(
                            controls=position_content,
                            spacing=2,
                            expand=True,
                            alignment=self.subtitle.get(
                                "alignment", ft.Alignment.TOP_CENTER
                            )
                            if self.subtitle is not None
                            else ft.Alignment.TOP_CENTER,
                        )

            # Build the M3 expand/collapse section from every "extra"
            # (4th+ auto-positioned) field - rendered as visible
            # "Label: value" rows, since - unlike leading/title/subtitle -
            # there's no other on-screen context for what an overflow
            # field is once it's hidden behind a tap.
            extra_rows = []
            for row_data in extra_position_data.values():
                for field_data in row_data:
                    name = field_data.get("name")
                    label_text = field_data.get("label_text") or name
                    value = record.get(name, "")
                    formatter = _FORMATTERS.get(field_data.get("format"))
                    display_value = (
                        formatter(value) if formatter and value not in (None, "") else value
                    )
                    extra_rows.append(
                        ft.Row(
                            controls=[
                                ft.Text(
                                    f"{label_text}:",
                                    size=12,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Text(
                                    str(display_value),
                                    size=12,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                            ],
                            spacing=6,
                        )
                    )

            expand_container = None
            trailing_content = tile_content.get("trailing")
            if extra_rows:
                expand_container = ft.Container(
                    content=ft.Column(controls=extra_rows, spacing=4),
                    padding=ft.Padding(left=16, top=4, right=16, bottom=12),
                    visible=False,
                )
                expand_button = ft.IconButton(
                    icon=_ICON_COLLAPSED,
                    tooltip="Show more",
                )
                expand_button.on_click = self._make_expand_toggle(
                    expand_container, expand_button
                )
                trailing_content = ft.Row(
                    controls=(
                        [trailing_content] if trailing_content is not None else []
                    )
                    + [expand_button],
                    spacing=0,
                    tight=True,
                )

            # create on_tap handler to navigate to edit page with key
            key_value = record.get(key_field) if key_field is not None else None
            on_tap_handler = (
                _make_tap(self.next_page, key_value) if key_field is not None else None
            )

            list_tile = ft.ListTile(
                title=tile_content.get("title"),
                subtitle=tile_content.get("subtitle"),
                subtitle_text_style=self.subtitle.get("subtitle_text_style")
                if self.subtitle is not None
                else None,
                leading=tile_content.get("leading"),
                trailing=trailing_content,
                on_click=on_tap_handler if on_tap_handler is not None else None,
            )
            # `ft.ListTile` itself paints an opaque background regardless
            # of its own `bgcolor` property (confirmed live - setting
            # `ListTile(bgcolor=...)` directly, and separately wrapping it
            # in a padded Container with its own bgcolor, both failed to
            # show any color at all) - so the zebra color is set on this
            # wrapping Container instead, which reliably renders bgcolor
            # everywhere else in this codebase (e.g. issue #53's flush
            # table-cell TextField wrapper).
            # Stacking the (collapsed) expand section below the ListTile
            # inside the same bgcolor Container only happens when there
            # actually are extra fields - a screen with none (e.g.
            # stock_in/index.py, which sets an explicit "position" on
            # every field) renders byte-for-byte the same tile tree as
            # before this issue, no regression.
            tile_body = ft.Column(controls=[list_tile, expand_container], spacing=0) \
                if expand_container is not None else list_tile
            self.tiles.append(
                ft.Container(
                    content=tile_body,
                    bgcolor=_TILE_COLOR_EVEN if tile_index % 2 == 0 else _TILE_COLOR_ODD,
                )
            )
            tile_index += 1
