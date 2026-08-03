import flet as ft

from components.form.input import (
    FIELD_BORDER_RADIUS,
    HELPER_TEXT_LINE_HEIGHT,
    HELPER_TEXT_STYLE,
    field_content_padding,
)
from components.scan_input import ScanInput
from components.table.menu import resolve_option_value
from utils.http_client import HttpClient

# Bounds the dropdown menu's visible height to roughly this many rows
# (Material 3's default ~48dp row height) - the menu stays scrollable for
# the rest, so a large master-data-backed select (materials, locations,
# ...) never dumps its entire option list open at once. Deliberately not a
# hard cap on the *option list itself* with a "show more" indicator (issue
# #26's original design) - that requires rebuilding Dropdown.options on
# every keystroke, which repeatedly broke Flutter's DropdownMenu focus.
# Flutter's own `enable_filter` does the actual typing-driven search
# entirely client-side (case-insensitive substring match against each
# option's full "CODE - Name" label, so it already matches code or name,
# anywhere in the string) with zero server round-trip.
_MENU_VISIBLE_ROWS = 5
_MENU_ROW_HEIGHT = 48

# The scan button sits next to the Dropdown, so it must be sized explicitly
# - an unconstrained IconButton carries Flutter's ~48dp tap target and
# visibly grows the row's height (issue #52).
SCAN_BUTTON_SIZE = 32
SCAN_ICON_SIZE = 20
SCAN_TRAILING_SPACING = 6


class SelectForm:
    """`"select"`-type form field: an `ft.Dropdown` with options fetched
    from `C_{module}/call_{name}_select`.

    Deliberately a thin wrapper around a plain, stock `ft.Dropdown`. Every
    piece of custom machinery this class used to carry has been removed
    after each was traced to a bug it was causing rather than fixing:

    * `_build_dropdown()` - rebuilt the whole control on every selection.
    * `_on_select()` - its rebuild never fixed issue #71.
    * a wrapping `ft.Container` - only ever existed to carry a fill colour
      that outlined fields don't have.
    * `schedule_notch_refresh()`/`_notch_refresh()` - a delayed post-mount
      `update()` "nudge" for a clipping bug whose real cause was
      too-small `content_padding` (see `input.py`).
    * `_on_focus()`/`_on_blur()` - **the actual cause of issue #71**, see
      below.
    * `refresh_with_values()`/`depends_on`/`depends_param` - a cascading
      select mechanism that no screen in this app has ever used.

    **Issue #71 - first pick via the text region did nothing.** Opening
    this field by tapping its text-input region (rather than the trailing
    arrow) and picking an option used to do nothing on the first attempt;
    a second pick worked, and opening via the arrow was never affected.
    Live instrumentation proved `on_select` never fired on the failing
    click, which was (wrongly) read as an unfixable upstream Flutter
    limitation.

    The real cause was this class's own `_on_focus` handler. Tapping the
    text region requests focus for the text field (that is what
    `editable=True` means, and it is what makes type-to-filter possible at
    all, issue #26), so `on_focus` fired, mutated `label_style` and called
    `update()` - pushing a control patch to the client *while the menu
    overlay was still opening*. The client rebuilt the Dropdown, the
    half-built overlay went with it, and the pending tap was lost. Tapping
    the trailing arrow never focuses the text field, so no patch was sent
    and that path always worked - and the second attempt worked because
    the field was already focused, so `on_focus` didn't fire again.

    Removing the handler removes the patch, and nothing is lost: Flutter
    already colours a focused field's floating label from the M3 theme via
    `floatingLabelStyle`, so leaving `label_style` without an explicit
    colour gets the same effect natively, with no round-trip.
    """

    def __init__(self, page: ft.Page, parent, field: dict, endpoint: str | None = None, custom_param: dict | None = None):
        self.page = page
        self.parent = parent
        self.module = parent.module
        self.screen = parent.screen
        self.name = field.get("name", "")
        self.label = field.get("label", "")
        self.hint_text = field.get("hint_text", f"Please input {self.label}")
        self.icon = field.get("icon")
        self.autofocus = field.get("autofocus", False)
        self.value_size = field.get("value_size", 14)
        self.label_size = field.get("label_size", 13)
        # M3 outlined colour roles (issue #79). No container fill, a full
        # border box. The focused label/border colours are left to
        # Flutter's own theme rather than swapped from Python - see the
        # class docstring on issue #71 for why that matters here.
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("label_color", ft.Colors.ON_SURFACE_VARIANT)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_border_color = field.get("focused_border_color", ft.Colors.PRIMARY)
        self.leading_icon = (
            ft.Icon(icon=self.icon, color=ft.Colors.ON_SURFACE_VARIANT)
            if self.icon is not None
            else None
        )
        # Outlined fields have no container fill by default (issue #79) -
        # still overridable per-field for a rare caller that wants one.
        self.filled = field.get("filled", False)
        self.bgcolor = field.get("bgcolor")
        self.enable_filter = field.get("enable_filter", True)
        self.editable = field.get("editable", True)
        # `enable_search` hands focus to a highlighted menu item, which is
        # a second thing competing for focus with the text field. Off by
        # default; it only controls "auto-highlight the entry matching what
        # is typed", NOT the type-to-filter narrowing (`enable_filter`).
        self.enable_search = field.get("enable_search", False)
        # Always present, even blank - an empty string still makes Flutter
        # reserve the supporting-text line, so every field type ends up the
        # same height without anyone forcing an explicit height.
        self.helper_text = field.get("helper_text", "")
        # Opt-in barcode/QR scan button beside this select (issue #52).
        self.qr = field.get("qr", False)
        self.scan_input: ScanInput | None = None
        self.select: ft.Dropdown | None = None
        self.data: list = []
        self.options: list = []
        self.custom_param: dict | None = custom_param
        self.endpoint = endpoint if endpoint is not None else f"C_{self.module}/call_{self.name}_select"

    def build(self):
        self.select = ft.Dropdown(
            label=self.label,
            hint_text=self.hint_text,
            hint_style=ft.TextStyle(color=ft.Colors.ON_SURFACE_VARIANT),
            leading_icon=self.leading_icon,
            helper_text=self.helper_text,
            helper_style=HELPER_TEXT_STYLE,
            border_radius=FIELD_BORDER_RADIUS,
            border=ft.InputBorder.OUTLINE,
            border_color=self.border_color,
            focused_border_color=self.focused_border_color,
            autofocus=self.autofocus,
            text_size=self.value_size,
            color=self.value_color,
            content_padding=field_content_padding(self.icon is not None),
            label_style=ft.TextStyle(size=self.label_size, color=self.label_color),
            filled=self.filled,
            fill_color=self.bgcolor,
            enable_filter=self.enable_filter,
            enable_search=self.enable_search,
            editable=self.editable,
            menu_height=_MENU_VISIBLE_ROWS * _MENU_ROW_HEIGHT,
            expand=True,
            options=[],
        )
        if not self.qr:
            return self.select

        # The scan button is a SIBLING of the Dropdown, not a child of its
        # decoration. It used to live inside the Dropdown's own
        # `trailing_icon` slot, but Flutter's MouseRegion-based hover
        # detection doesn't stop at a nested child's bounds the way tap
        # hit-testing does - hovering anywhere in the decoration lit up the
        # whole field's hover overlay, making the scan button and the
        # dropdown arrow look like they shared one hover state (issue #52
        # follow-up). As siblings, each lights up independently.
        self.scan_input = ScanInput(
            page=self.page,
            on_scan=self.apply_scanned_code,
            title=f"Scan {self.label}" if self.label else "Scan Barcode / QR",
            tooltip=f"Scan {self.label}" if self.label else "Scan barcode / QR",
            icon_size=SCAN_ICON_SIZE,
            width=SCAN_BUTTON_SIZE,
            height=SCAN_BUTTON_SIZE,
        )
        return ft.Row(
            controls=[
                self.select,
                # The Dropdown's full height is its input box PLUS the
                # reserved helper-text line underneath, so centring the
                # button against the whole thing leaves it sitting visibly
                # low. A bottom margin of the helper line's height shifts
                # it up by half that, landing it on the box's own centre.
                ft.Container(
                    content=self.scan_input.build(),
                    margin=ft.Margin.only(bottom=HELPER_TEXT_LINE_HEIGHT),
                ),
            ],
            spacing=SCAN_TRAILING_SPACING,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def apply_scanned_code(self, code: str) -> None:
        """Select the option a scanned code refers to (issue #52).

        Matching is delegated to `resolve_option_value()` (issue #25) so a
        bare code (`SKU-1`), a full `"SKU-1 - Widget"` label and a raw DB id
        all work, with exactly one matching rule app-wide.
        """
        options = [
            (str(opt.get("value", "")), str(opt.get("label", "")))
            for opt in self.data or []
        ]
        resolved = resolve_option_value(code, options)
        if resolved is None:
            self._show_error(f"No {self.label or 'match'} found for '{code}'")
            return

        self.select.value = resolved
        self.select.update()

    def _show_error(self, message: str) -> None:
        """Surface an unmatched scan instead of silently doing nothing."""
        view = getattr(self.parent, "view", None)
        if view is not None and hasattr(view, "show_error"):
            view.show_error(message)
        else:
            print(message)

    def get_data(self):
        client = HttpClient(self.page)

        params = self.custom_param.copy() if self.custom_param else {}
        if getattr(self.parent, "record_id", None):
            params["record_id"] = self.parent.record_id

        response = client.get(self.endpoint, params if params else None)
        if isinstance(response, dict) and "error" in response:
            print(f"Error fetching data: {response.get('error')}")
            return

        if isinstance(response, list):
            self.data = response

    def rebuild(self):
        """Fetch this select's options and load them into the control."""
        self.get_data()

        if not isinstance(self.select, ft.Dropdown) or not isinstance(self.data, list):
            return

        self.options = [
            ft.DropdownOption(
                key=item.get("value", ""),
                text=item.get("label", item.get("value", "")),
            )
            for item in self.data
        ]
        self.select.options = self.options
