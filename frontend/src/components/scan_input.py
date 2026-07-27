"""Reusable barcode/QR scan affordance (issue #52).

The scanner is a **hardware gun acting as a keyboard wedge** - it types the
scanned code followed by Enter into whatever field currently has focus. It is
NOT a camera scanner, so there is no dependency, no camera permission flow,
and this works identically on web (where this app actually runs) and native.

Because the gun types wherever focus happens to be, the button's real job is
to give the operator an unambiguous scan target: it opens a tiny dialog whose
single `ft.TextField` is autofocused, so the very next scan lands there and
its Enter fires `on_submit`. That is the same pattern senar's own "Scan Segel"
screen uses (`tm_confirm_seal_mobile/scan.py` - autofocus plus `on_submit`),
which is the only scanning implementation that repo actually has; there was no
camera scanner there to port.

Callers supply `on_scan(code: str)` and decide what a code means - this
component never resolves codes itself. For option-backed pickers, resolve via
`components/table/menu.py::resolve_option_value()` so the app keeps exactly
one matching rule (raw id / full label / `"{code} - {name}"` prefix, issue
#25); do not write a second matcher.
"""

import flet as ft


class ScanInput:
    """A scan button that collects one scanned code and hands it to `on_scan`."""

    def __init__(
        self,
        page: ft.Page,
        on_scan,
        title: str = "Scan Barcode / QR",
        hint_text: str = "Scan or type a code, then press Enter",
        tooltip: str = "Scan barcode / QR",
        icon_size: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ):
        self.page = page
        self.on_scan = on_scan
        self.title = title
        self.hint_text = hint_text
        self.tooltip = tooltip
        self.icon_size = icon_size
        self.width = width
        self.height = height
        self.dialog: ft.AlertDialog | None = None
        self.field: ft.TextField | None = None

    def build(self) -> ft.IconButton:
        return ft.IconButton(
            icon=ft.Icons.QR_CODE_SCANNER,
            tooltip=self.tooltip,
            on_click=self._open,
            icon_size=self.icon_size,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            width=self.width,
            height=self.height,
            padding=0 if self.width or self.height else None,
        )

    def _open(self, e=None) -> None:
        # Built fresh per open rather than reused: a scanner dialog is
        # short-lived and must always come up empty and focused, and
        # rebuilding sidesteps the stale-control/focus problems this codebase
        # has hit before when re-showing a cached control (see
        # components/table/menu.py's own Flet-invariant notes).
        self.field = ft.TextField(
            hint_text=self.hint_text,
            autofocus=True,
            border_radius=10,
            on_submit=self._submit,
        )
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(self.title),
            content=ft.Container(content=self.field, width=360),
            actions=[ft.TextButton("Cancel", on_click=self._cancel)],
        )
        self.page.overlay.append(self.dialog)
        self.dialog.open = True
        self._safe_page_update()

    def _submit(self, e=None) -> None:
        code = (self.field.value or "").strip() if self.field else ""
        self._close()
        if code and self.on_scan:
            self.on_scan(code)

    def _cancel(self, e=None) -> None:
        self._close()

    def _close(self) -> None:
        if self.dialog is not None:
            self.dialog.open = False
        self._safe_page_update()

    def _safe_page_update(self) -> None:
        try:
            self.page.update()
        except RuntimeError:
            pass
