import flet as ft

from components.scan_input import ScanInput

# The scan button lives inside the field's own suffix_icon slot, so it must
# be sized explicitly - an unconstrained IconButton there carries Flutter's
# ~48dp tap target and visibly grows the field's height (same as
# components/form/select.py's own scan button, issue #52).
SCAN_BUTTON_SIZE = 24
SCAN_ICON_SIZE = 18


class InputForm:

    def __init__(self, page: ft.Page, field: dict):
        self.page = page
        self.label = field.get("label", "")
        self.hint_text = field.get("hint_text", f"Please input {self.label}")
        self.icon = field.get("icon")
        self.autofocus = field.get("autofocus", False)
        self.read_only = field.get("read_only", False)
        self.value_size = field.get("value_size", 14)
        self.label_size = field.get("label_size", 13)
        # M3 filled text field color roles (issue #53 follow-up, corrected
        # against the real spec at m3.material.io/components/text-fields/specs
        # after an initial custom PRIMARY_CONTAINER/TERTIARY_CONTAINER
        # background-swap design was found to diverge from it): container
        # fill is SURFACE_CONTAINER_HIGHEST and stays constant across
        # states (M3 does NOT swap the fill on focus); input text is a
        # constant ON_SURFACE; the label is ON_SURFACE_VARIANT at rest and
        # turns PRIMARY on focus - only the label's color changes here.
        # The field also keeps M3's "active indicator" bottom border (a
        # further correction, same day): ON_SURFACE_VARIANT at rest,
        # PRIMARY focused - `ft.InputBorder.UNDERLINE` plus
        # `focused_border_color` handle this natively (Flutter's own
        # underline decoration swaps it on focus without needing the
        # manual on_focus/on_blur workaround `focused_bgcolor` needed).
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("label_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_label_color = field.get("focused_label_color", ft.Colors.PRIMARY)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_border_color = field.get("focused_border_color", ft.Colors.PRIMARY)
        self.multiline = field.get("multiline", False)
        self.min_lines = field.get("min_lines", 1)
        self.max_lines = field.get("max_lines", 1)
        self.prefix_icon = None
        self.filled = field.get("filled", True)
        self.bgcolor = field.get("bgcolor", ft.Colors.SURFACE_CONTAINER_HIGHEST)
        self.password = field.get("password", False)
        self.can_reveal_password = field.get("can_reveal_password", self.password)
        # Opt-in barcode/QR scan button (issue #52 parity for plain text
        # inputs, added on request) - off unless the field dict says
        # `"qr": True`, so every existing input in the app is untouched.
        # Unlike select.py's scan button, a scanned code here isn't
        # resolved against a fixed option list - it's typed straight into
        # the field, so it lives in the field's own suffix_icon slot (no
        # sibling-control/hover-isolation concern the way Dropdown's own
        # trailing arrow had in issue #52's follow-up).
        self.qr = field.get("qr", False)
        self.scan_input: ScanInput | None = None
        self.field: ft.TextField | None = None

    def build(self):
        self.prefix_icon = (
            ft.Icon(
                icon=self.icon,
                color=ft.Colors.ON_SURFACE_VARIANT) if self.icon is not None else None
        )
        is_focused = self.autofocus
        suffix_icon = None
        suffix_icon_size_constraints = None
        if self.qr:
            self.scan_input = ScanInput(
                page=self.page,
                on_scan=self.apply_scanned_code,
                title=f"Scan {self.label}" if self.label else "Scan Barcode / QR",
                tooltip=f"Scan {self.label}" if self.label else "Scan barcode / QR",
                icon_size=SCAN_ICON_SIZE,
                width=SCAN_BUTTON_SIZE,
                height=SCAN_BUTTON_SIZE,
            )
            suffix_icon = self.scan_input.build()
            suffix_icon_size_constraints = ft.BoxConstraints(
                min_width=SCAN_BUTTON_SIZE,
                max_width=SCAN_BUTTON_SIZE,
                min_height=SCAN_BUTTON_SIZE,
                max_height=SCAN_BUTTON_SIZE,
            )
        self.field = ft.TextField(
            label=self.label,
            hint_text=self.hint_text,
            hint_style=ft.TextStyle(color=ft.Colors.ON_SURFACE_VARIANT),
            prefix_icon=self.prefix_icon,
            suffix_icon=suffix_icon,
            suffix_icon_size_constraints=suffix_icon_size_constraints,
            border_radius=10,
            border=ft.InputBorder.UNDERLINE,
            border_color=self.border_color,
            focused_border_color=self.focused_border_color,
            autofocus=self.autofocus,
            text_size=self.value_size,
            read_only=self.read_only,
            color=self.value_color,
            # M3 spec: 8dp top/bottom, 16dp left/right (12dp with an icon).
            content_padding=ft.Padding.only(
                left=12 if self.icon else 16, right=16, top=8, bottom=8
            ),
            label_style=ft.TextStyle(
                size=self.label_size,
                color=self.focused_label_color if is_focused else self.label_color,
            ),
            multiline=self.multiline,
            min_lines=self.min_lines,
            max_lines=self.max_lines,
            filled=self.filled,
            bgcolor=self.bgcolor,
            password=self.password,
            can_reveal_password=self.can_reveal_password,
            adaptive=True,
            expand=True,
            # Only the label's color needs a live swap on focus (per spec) -
            # the border color is handled natively by
            # `focused_border_color` above.
            on_focus=self._on_focus,
            on_blur=self._on_blur,
        )
        return self.field

    def _on_focus(self, e=None) -> None:
        self.field.label_style = ft.TextStyle(size=self.label_size, color=self.focused_label_color)
        self._safe_update()

    def _on_blur(self, e=None) -> None:
        self.field.label_style = ft.TextStyle(size=self.label_size, color=self.label_color)
        self._safe_update()

    def apply_scanned_code(self, code: str) -> None:
        """A scanned code is typed straight into the field - no option list
        to resolve against here, unlike select.py's own scan handler."""
        if self.field is not None:
            self.field.value = code
            self._safe_update()

    def _safe_update(self) -> None:
        try:
            self.field.update()
        except RuntimeError:
            pass
