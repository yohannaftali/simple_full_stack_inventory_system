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
        self.value_size = field.get("value_size", 16)
        self.label_size = field.get("label_size", 14)
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE)
        self.leading_icon = None
        self.filled = field.get("filled", False)
        self.bgcolor = field.get("bgcolor", ft.Colors.SURFACE)
        self.enable_filter = field.get("enable_filter", True)
        self.editable = field.get("editable", True)
        # Opt-in barcode/QR scan button beside this select (issue #52) - off
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

    def build(self):
        self.leading_icon = (
            ft.Icon(
                icon=self.icon,
                color=self.value_color) if self.icon is not None else None
        )
        self.select = ft.Dropdown(
            label=self.label,
            hint_text=self.hint_text,
            leading_icon=self.leading_icon,
            border_radius=10,
            border_color=self.border_color,
            autofocus=self.autofocus,
            text_size=self.value_size,
            color=self.value_color,
            label_style=ft.TextStyle(
                size=self.label_size,
                color=self.label_color,
            ),
            filled=self.filled,
            bgcolor=self.bgcolor,
            enable_filter=self.enable_filter,
            editable=self.editable,
            menu_height=_MENU_VISIBLE_ROWS * _MENU_ROW_HEIGHT,
            expand=True,
        )
        if not self.qr:
            return self.select

        # The scan button sits BESIDE the Dropdown, not inside it. Flet's
        # Dropdown (a Flutter DropdownMenu) owns its trailing slot for the
        # open/close arrow: `trailing_icon` *replaces* that arrow rather than
        # sitting next to it, and isn't independently clickable - so putting
        # the QR icon inside the field would cost the arrow affordance. A Row
        # keeps both. Note `build()` therefore no longer always returns a
        # Dropdown; `Form.load()`/`serialize()` read `Form.select[name].select`
        # rather than isinstance-checking the built control for that reason.
        self.scan_input = ScanInput(
            page=self.page,
            on_scan=self.apply_scanned_code,
            title=f"Scan {self.label}" if self.label else "Scan Barcode / QR",
            tooltip=f"Scan {self.label}" if self.label else "Scan barcode / QR",
        )
        return ft.Row(
            controls=[self.select, self.scan_input.build()],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
