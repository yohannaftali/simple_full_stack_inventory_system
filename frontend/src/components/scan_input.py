"""Reusable barcode/QR scan affordance (issue #52, camera/photo path issue #64).

Two independent ways to feed a code into `on_scan(code: str)`:

1. **Hardware gun acting as a keyboard wedge** (issue #52, the original and
   still-default path) - it types the scanned code followed by Enter into
   whatever field currently has focus. The button's job here is to give the
   operator an unambiguous scan target: opening the dialog autofocuses a
   plain `ft.TextField`, so the very next scan lands there and its Enter
   fires `on_submit`. Same pattern senar's own "Scan Segel" screen uses
   (`tm_confirm_seal_mobile/scan.py` - autofocus plus `on_submit`).

2. **Camera/photo capture + server-side decode** (issue #64) - a "Scan with
   Photo" button next to the manual-entry field opens `ft.FilePicker(
   file_type=IMAGE, with_data=True)`, which opens the device camera for one
   photo on platforms that support it (mobile browsers, native) or a plain
   file browser otherwise - this app's containerized web deployment runs the
   Flet process server-side (see AGENTS.md's "Container networking gotcha"),
   so a live in-Python camera read (e.g. `cv2.VideoCapture`) would read the
   *server container's* camera, not the end user's - only bytes the browser
   itself already delivered to Python are ever correct here. The picked
   photo's bytes are decoded with `pyzbar` (native `libzbar`, installed in
   frontend/Dockerfile). A **genuine live in-browser scan** (matching
   senar's own `html5-qrcode`-based `handleScanCamera()` in
   `code/public/js/framework/y.form.js`, including front/rear camera
   switching) was investigated for this issue and intentionally NOT built:
   Flet 0.85.3 has no WebView/JS-eval control to embed a third-party JS
   library the way senar's own HTML page does, and the one real Flutter-side
   candidate found on PyPI (`flet-camera`, camera *preview/photo* only, no
   barcode decoding of its own) only ships stable releases pinned to
   flet==0.86.4 - its 0.85.3 releases are `.dev0`/`.dev1` prereleases, too
   risky to pin in this app's locked `flet==0.85.3`. Left as a documented,
   larger future follow-up (a custom Flet extension wrapping a live-scan
   Flutter plugin), not attempted here.

Callers supply `on_scan(code: str)` and decide what a code means - this
component never resolves codes itself, regardless of which path produced the
code. For option-backed pickers, resolve via
`components/table/menu.py::resolve_option_value()` so the app keeps exactly
one matching rule (raw id / full label / `"{code} - {name}"` prefix, issue
#25); do not write a second matcher.
"""

import io

import flet as ft
from PIL import Image, UnidentifiedImageError
from pyzbar.pyzbar import decode as zbar_decode


def decode_image_bytes(data: bytes) -> str | None:
    """Decode the first barcode/QR found in raw image bytes, or `None` if
    none is found / the bytes aren't a decodable image. A thin wrapper
    around `pyzbar` so the dialog-building code below and any future
    non-UI caller (e.g. a test) share one decode path."""
    try:
        image = Image.open(io.BytesIO(data))
    except UnidentifiedImageError:
        return None
    results = zbar_decode(image)
    if not results:
        return None
    return results[0].data.decode("utf-8", errors="replace")


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
        self.error_text: ft.Text | None = None
        self.file_picker: ft.FilePicker | None = None

    def build(self) -> ft.IconButton:
        # `width`/`height` alone only set this control's own layout box -
        # Flutter's Material IconButton still applies its own default
        # minimum tap-target constraints (~40-48dp) to the ink/hover
        # region underneath regardless of that box, so a 24x24 button
        # sitting a few px from a neighboring icon (the dropdown's own
        # arrow, or another trailing icon) had its hover/splash circle
        # visibly overflow past its own bounds and bleed onto that
        # neighbor - the "hovering one highlights the other, and one
        # shows extra highlight behind it" symptom reported for issue
        # #52's select/dropdown scan button. `size_constraints` is the
        # one IconButton property that actually clamps that internal
        # tap-target/ink region itself, not just the outer layout box.
        size_constraints = (
            ft.BoxConstraints(
                min_width=self.width or self.icon_size or 24,
                max_width=self.width or self.icon_size or 24,
                min_height=self.height or self.icon_size or 24,
                max_height=self.height or self.icon_size or 24,
            )
            if self.width or self.height
            else None
        )
        return ft.IconButton(
            icon=ft.Icons.QR_CODE_SCANNER,
            tooltip=self.tooltip,
            on_click=self._open,
            icon_size=self.icon_size,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            width=self.width,
            height=self.height,
            padding=0 if self.width or self.height else None,
            size_constraints=size_constraints,
        )

    def _open(self, e=None, error_text: str | None = None) -> None:
        # Built fresh per open rather than reused: a scanner dialog is
        # short-lived and must always come up empty and focused, and
        # rebuilding sidesteps the stale-control/focus problems this codebase
        # has hit before when re-showing a cached control (see
        # components/table/menu.py's own Flet-invariant notes). `error_text`
        # is set when this is a retry-reopen after a photo scan found no
        # decodable code (issue #64's "never a silent failure" requirement).
        self.field = ft.TextField(
            hint_text=self.hint_text,
            autofocus=True,
            border_radius=10,
            on_submit=self._submit,
        )
        self.error_text = ft.Text(
            error_text or "", color=ft.Colors.ERROR, size=12, visible=bool(error_text)
        )
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(self.title),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        self.field,
                        self.error_text,
                        ft.TextButton(
                            content="Scan with Photo",
                            icon=ft.Icons.PHOTO_CAMERA_OUTLINED,
                            on_click=self._pick_photo,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                width=360,
            ),
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

    # ---------------------------------------------------------- photo scan

    async def _pick_photo(self, e=None) -> None:
        # Must be a real `async def` handler, not a sync lambda wrapping an
        # async call - Flet's dispatcher only awaits a handler that IS a
        # coroutine function; a sync wrapper gets its returned coroutine
        # silently dropped (see components/table/menu.py's own note on this
        # exact Flet 0.85.3 invariant).
        #
        # Lazy picker creation/registration, same reasoning as
        # components/table/menu.py::TableMenu._pick_and_populate(): FilePicker
        # is a `Service` (not a visual Control) so it belongs in
        # `page.services`, not `page.overlay` - and `page.services` resolves
        # through the root view, which doesn't exist yet during a
        # ModulePage's own __init__ but does exist here, inside a live click
        # handler on the event loop.
        if self.file_picker is None:
            self.file_picker = ft.FilePicker()
        if self.file_picker not in self.page.services:
            self.page.services.append(self.file_picker)
            self.page.update()

        self._close()
        files = await self.file_picker.pick_files(
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False,
            with_data=True,
        )
        if not files:
            # User cancelled the picker - reopen the manual-entry dialog
            # with no error, same as a plain Cancel.
            self._open()
            return

        picked = files[0]
        data = picked.bytes
        if data is None and picked.path:
            # Native fallback: some platforms hand back a path only (same
            # pattern as components/table/menu.py::_pick_and_populate).
            try:
                with open(picked.path, "rb") as f:
                    data = f.read()
            except OSError:
                data = None
        if data is None:
            self._open(error_text="Could not read the selected photo. Try again.")
            return

        code = decode_image_bytes(data)
        if code:
            if self.on_scan:
                self.on_scan(code)
            return

        # "Never a silent failure" (issue #64 acceptance criteria) - reopen
        # the same dialog with an error and let the user retry the photo or
        # fall back to manual/hardware-scanner entry.
        self._open(
            error_text="No barcode/QR found in that photo. Try again or enter the code manually."
        )
