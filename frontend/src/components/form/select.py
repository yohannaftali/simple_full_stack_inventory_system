import flet as ft

from components.scan_input import ScanInput
from components.table.menu import resolve_option_value
from utils.http_client import HttpClient

# Bounds the dropdown menu's visible height to roughly this many rows
# (Material 3's default ~48dp row height) - the menu stays scrollable for
# the rest, so a large master-data-backed select (materials, locations,
# ...) never dumps its entire option list open at once. Deliberately not a
# hard cap on the *option list itself* with a "show more" indicator (issue
# #26's original design) - that requires rebuilding Dropdown.options on
# every keystroke, which repeatedly broke Flutter's DropdownMenu focus
# (see AGENTS.md's "Capped/'show more' select filtering" entry for the full
# history). Flutter's own `enable_filter` does the actual typing-driven
# search entirely client-side (case-insensitive substring match against
# each option's full "CODE - Name" label, so it already matches code or
# name, anywhere in the string) with zero server round-trip, which is what
# makes it reliable.
_MENU_VISIBLE_ROWS = 5
_MENU_ROW_HEIGHT = 48

# The scan button lives inside the field's decoration box, so it must be
# sized explicitly - an unconstrained IconButton there carries Flutter's
# ~48dp tap target and visibly grows the field's height (the same ballooning
# a Control-typed suffix_icon caused on TextField, issue #52).
SCAN_BUTTON_SIZE = 24
SCAN_ICON_SIZE = 18
# Gap between the scan button and the open/close arrow sharing the trailing
# slot, so the two don't read as one control.
SCAN_TRAILING_SPACING = 6


class SelectForm:

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
        # M3 filled text field color roles - see components/form/input.py's
        # class docstring for the full spec-correction rationale (issue #53
        # follow-up). Fill/text are constant; only the label turns PRIMARY
        # on focus. `ft.Dropdown` has no `focused_bgcolor`/live-swappable
        # fill of its own (its `bgcolor` prop colors the *popup menu*, not
        # the field), so the constant fill is still applied via a wrapping
        # `ft.Container` (see `build()`) - the Dropdown itself renders
        # transparent (`fill_color=TRANSPARENT`) so the wrapper's color
        # shows through; only `label_style` needs a live on_focus/on_blur
        # swap now.
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("label_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_label_color = field.get("focused_label_color", ft.Colors.PRIMARY)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_border_color = field.get("focused_border_color", ft.Colors.PRIMARY)
        self.leading_icon = None
        self.filled = field.get("filled", True)
        self.bgcolor = field.get("bgcolor", ft.Colors.SURFACE_CONTAINER_HIGHEST)
        self.container: ft.Container | None = None
        self.enable_filter = field.get("enable_filter", True)
        self.editable = field.get("editable", True)
        # Opt-in barcode/QR scan button inside this select (issue #52) - off
        # unless the field dict says `"qr": True`, so every existing select
        # in the app is untouched.
        self.qr = field.get("qr", False)
        self.scan_input: ScanInput | None = None
        self.select = None
        self.data: list = []
        self.options: list = []
        self.custom_param: dict | None = custom_param
        self.endpoint = endpoint if endpoint is not None else f"C_{self.module}/call_{self.name}_select"
        # depends_on: field name that this select depends on
        # When the parent field changes, this select will refresh with new params
        self.depends_on = field.get("depends_on", None)
        # depends_param: the parameter name to send with the parent field's value
        self.depends_param = field.get("depends_param", self.depends_on)

    def _build_dropdown(self, value=None, text=None, options=None) -> ft.Dropdown:
        """Construct a brand-new `ft.Dropdown` control instance.

        Factored out of `build()` so `_on_select()` can rebuild the control
        from scratch instead of patching the existing instance's `.text` -
        see `_on_select()`'s own comment for why a patch alone isn't
        reliable here (confirmed via live server-log instrumentation,
        2026-07-30: the server-side `.text`/`.value` were already correct
        before the patch, yet the browser still didn't repaint - a client
        patch-application bug, not a value bug). This mirrors the same
        "force a full control rebuild instead of trusting an in-place
        patch" fix this app already relies on elsewhere (`DataRow.color`,
        header rebuilds for the resize/sort-icon fixes).
        """
        return ft.Dropdown(
            label=self.label,
            hint_text=self.hint_text,
            hint_style=ft.TextStyle(color=ft.Colors.ON_SURFACE_VARIANT),
            leading_icon=self.leading_icon,
            border_radius=0,
            border=ft.InputBorder.UNDERLINE,
            border_color=self.border_color,
            focused_border_color=self.focused_border_color,
            autofocus=self.autofocus,
            text_size=self.value_size,
            color=self.value_color,
            content_padding=ft.Padding.only(
                left=12 if self.icon else 16, right=16, top=8, bottom=8
            ),
            label_style=ft.TextStyle(
                size=self.label_size,
                color=self.label_color,
            ),
            filled=self.filled,
            fill_color=ft.Colors.TRANSPARENT,
            enable_filter=self.enable_filter,
            editable=self.editable,
            menu_height=_MENU_VISIBLE_ROWS * _MENU_ROW_HEIGHT,
            expand=True,
            options=options if options is not None else [],
            value=value,
            text=text,
            on_focus=self._on_focus,
            on_blur=self._on_blur,
            on_select=self._on_select,
        )

    def build(self):
        self.leading_icon = (
            ft.Icon(
                icon=self.icon,
                color=ft.Colors.ON_SURFACE_VARIANT) if self.icon is not None else None
        )
        self.select = self._build_dropdown()
        self.container = ft.Container(
            bgcolor=self.bgcolor,
            border_radius=0,
            padding=0,
            expand=True,
        )
        if not self.qr:
            self.container.content = self.select
            return self.container

        # The scan button used to sit INSIDE the field's own trailing_icon
        # slot, next to the open/close arrow. That put both controls inside
        # the Dropdown's own decoration box, and Flutter's MouseRegion-based
        # hover detection doesn't stop at a nested child's bounds the way
        # tap/click hit-testing does - hovering *anywhere* in the decoration
        # (the label, blank space, either icon) lit up the whole field's own
        # hover overlay, which made the scan button and the arrow look like
        # they shared one hover state (reported live, 2026-07-28). The two
        # can only be made to look and behave fully independently by taking
        # the scan button out of the Dropdown's decoration entirely - a
        # sibling control next to it, not a child inside it - so its own
        # IconButton hover/ripple is the only thing that ever lights up when
        # hovering it, and the Dropdown's own field-level hover is the only
        # thing that lights up for the rest of the field (label, arrow,
        # blank space), each independent of the other.
        self.scan_input = ScanInput(
            page=self.page,
            on_scan=self.apply_scanned_code,
            title=f"Scan {self.label}" if self.label else "Scan Barcode / QR",
            tooltip=f"Scan {self.label}" if self.label else "Scan barcode / QR",
            icon_size=SCAN_ICON_SIZE,
            width=SCAN_BUTTON_SIZE,
            height=SCAN_BUTTON_SIZE,
        )
        # The scan button is a sibling control, not part of the Dropdown's
        # own decoration (see the class-level docstring for why), so it
        # doesn't inherit the Dropdown's own right-side content_padding -
        # without an explicit right inset here it sat flush against the
        # container's true right edge, unlike every other trailing icon in
        # the app (the QR button's own trailing arrow, the table search
        # bar's icons, etc.), which all sit inside a padded decoration box.
        self.container.padding = ft.Padding.only(right=8)
        self.container.content = ft.Row(
            controls=[self.select, self.scan_input.build()],
            spacing=SCAN_TRAILING_SPACING,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        return self.container

    def _on_focus(self, e=None) -> None:
        self.select.label_style = ft.TextStyle(size=self.label_size, color=self.focused_label_color)
        self._safe_container_update()

    def _on_blur(self, e=None) -> None:
        self.select.label_style = ft.TextStyle(size=self.label_size, color=self.label_color)
        self._safe_container_update()

    def _on_select(self, e=None) -> None:
        # Real, user-reported bug (issue #71): opening this field by tapping
        # directly in its text-input region (vs. the trailing arrow) and
        # picking the FIRST option leaves the displayed text unchanged -
        # picking again (second attempt) works correctly. Opening via the
        # arrow never has this problem.
        #
        # ROOT CAUSE, confirmed 2026-07-30 via live server-log instrumentation
        # against the real containerized app (not automation - CDP-driven
        # synthetic clicks could never reproduce this bug at all, only the
        # user's real physical clicks could): on the failing first click,
        # this handler NEVER FIRES - zero log output, verified with a clean
        # `podman logs --since <now> -f` stream (an earlier round that
        # appeared to show it firing/succeeding was contaminated by `podman
        # logs -f`'s default behavior of replaying a container's ENTIRE
        # historical log on every new invocation, not fresh output - a
        # methodology mistake in this investigation, not evidence about the
        # app). This means the click event is never dispatched from the
        # Flutter client to the server at all on this interaction path - no
        # Python code here, however written, can fix a callback that is
        # never invoked.
        #
        # This matches a known class of real Flutter bug: when a
        # `DropdownMenu`-style widget's text field gains keyboard focus as
        # part of opening (exactly what `editable=True` does, needed for the
        # type-to-filter feature from issue #26), the very first tap
        # afterward is consumed by Flutter's own focus-settling handshake
        # instead of registering as "select this item" - the second tap
        # works because focus has already settled. Opening via the arrow
        # never gives the text field focus, so it never hits this trap.
        # This is a genuine upstream Flutter/Flet limitation, not a bug in
        # this app's Python code - per explicit user decision (2026-07-30),
        # left as a documented known limitation rather than removing
        # `editable`/`enable_filter` (which would trade this bug away for
        # losing type-to-filter everywhere). See AGENTS.md issue #71 for the
        # full investigation history.
        #
        # This handler still corrects the display on every click that DOES
        # reach the server (e.g. the second, working pick) - rebuilding a
        # brand-new Dropdown control rather than patching the existing
        # instance's `.text`, since in-place patching was separately proven
        # unreliable on this widget (also confirmed via the same
        # instrumentation): the server-side value/text were already correct
        # before a patch was even applied, yet the browser didn't repaint -
        # the same "don't trust an in-place patch, force a rebuild" lesson
        # this app already learned from `DataRow.color` and the header
        # resize/sort-icon fixes.
        matched = next(
            (opt for opt in self.select.options if opt.key == self.select.value),
            None,
        )
        if matched is None:
            return
        self.select = self._build_dropdown(
            value=matched.key, text=matched.text, options=self.select.options
        )
        if not self.qr:
            self.container.content = self.select
        else:
            self.container.content.controls[0] = self.select
        self._safe_container_update()

    def _safe_container_update(self) -> None:
        try:
            self.container.update()
        except RuntimeError:
            pass

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
        self._safe_update()

    def _show_error(self, message: str) -> None:
        """Surface an unmatched scan instead of silently doing nothing."""
        view = getattr(self.parent, "view", None)
        if view is not None and hasattr(view, "show_error"):
            view.show_error(message)
        else:
            print(message)

    def get_data(self, extra_params: dict = None):
        client = HttpClient(self.page)

        params = self.custom_param.copy() if self.custom_param else {}
        if hasattr(self.parent, 'record_id') and self.parent.record_id:
            params['record_id'] = self.parent.record_id

        # Add extra params (e.g., from depends_on field)
        if extra_params:
            params.update(extra_params)

        response = client.get(self.endpoint, params if params else None)
        if isinstance(response, dict) and "error" in response:
            print(f"Error fetching data: {response.get('error')}")
            return

        if isinstance(response, list):
            self.data = response

    def rebuild(self, extra_params: dict = None):
        # If this select depends on another field and no parent value provided yet,
        # but only if check strict dependency (optional logic, for now we assume strict if params missing)
        # Note: We now check if ALL required dependencies are present in extra_params if we want to be strict
        # For simple cascading, we just check if extra_params is provided at all

        if self.depends_on and not extra_params:
            self.data = []
            if self.select:
                self.select.options = []
            return

        self.get_data(extra_params)

        if not isinstance(self.select, ft.Dropdown):
            return

        if not isinstance(self.data, list):
            return

        self.options = []
        for item in self.data:
            option_value = item.get("value", "")
            option_label = item.get("label", option_value)
            self.options.append(ft.DropdownOption(
                key=option_value, text=option_label))
        self.select.options = self.options

    def refresh_with_values(self, form_values: dict):
        """Refresh options using current form values"""
        # Clear current value and options
        if self.select:
            self.select.value = None
            self.select.options = []

        # If depends_on is set, check if the dependent value is present
        # Support single string depends_on for now, or we can logic check
        if self.depends_on:
            # depends_on can be a single field or list of fields (future proofing)
            deps = [self.depends_on] if isinstance(self.depends_on, str) else self.depends_on

            # Check if primary dependency is present in form_values
            # and verify it has a value
            missing_dep = False
            for dep in deps:
                if not form_values.get(dep):
                    missing_dep = True
                    break

            if missing_dep:
                # Dependency missing or empty, clear options and return
                self.data = []
                if self.select:
                    self._safe_update()
                return

        # Load options with full form values as params
        # This allows backend to pick whatever params it needs
        self.rebuild(form_values)

        # Update the UI
        if self.select:
            self._safe_update()

    def _safe_update(self):
        """Update the select control if it's already mounted on the page.

        refresh_with_values() can run during the initial Form.build() (e.g.
        an edit screen pre-populating a cascading select), before the
        control tree has been appended to page.views. Control.update()
        raises RuntimeError in that case since Flet 0.85 - the eventual
        page.update() once the view is mounted will render the values
        already assigned above, so a failed early update is safe to skip.
        """
        try:
            self.select.update()
        except RuntimeError:
            pass
