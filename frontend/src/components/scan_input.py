"""Reusable barcode/QR scan affordance (issue #52, camera/photo path issue
#64, live camera scan issue #64 follow-up 2026-07-29).

Three independent ways to feed a code into `on_scan(code: str)`:

1. **Hardware gun acting as a keyboard wedge** (issue #52, the original and
   still-available path) - it types the scanned code followed by Enter into
   whatever field currently has focus. Opening the manual-entry dialog
   autofocuses a plain `ft.TextField`, so the very next scan lands there and
   its Enter fires `on_submit`. Same pattern senar's own "Scan Segel" screen
   uses (`tm_confirm_seal_mobile/scan.py` - autofocus plus `on_submit`).

2. **Live in-browser camera scan** (issue #64 follow-up, once
   `flet==0.86.4` unblocked it - see below) - clicking the scan button opens
   a real live camera preview via `flet_camera.Camera`, decoding each
   incoming frame with the same `pyzbar` path as (3) below, throttled to
   avoid pegging the CPU on every single frame. `flet-camera` wraps
   Flutter's own `camera` plugin (Web/iOS/Android support - confirmed via
   its own PyPI platform-support table), so on the web deployment the
   browser itself captures frames client-side via `getUserMedia` under the
   hood - this is NOT the same thing as reading a camera from Python
   (`cv2.VideoCapture` or similar), which would read the *server
   container's* camera (this app's containerized web deployment runs the
   Flet process server-side - see AGENTS.md's "Container networking
   gotcha") - there is no camera device in that container at all, so a
   pure-OpenCV approach is fundamentally the wrong mechanism for this app's
   primary deployment regardless of how well it works in a plain desktop
   script. `flet-camera`'s stable releases have only ever matched
   `flet==0.86.4` - unblocked by that upgrade (issue #68), not available
   for this app's previous `flet==0.85.3` pin.
3. **Camera/photo capture + server-side decode** (issue #64 v1, kept as the
   graceful-degradation path when no camera is available/permitted, and as
   an explicit "choose from gallery" option) - `ft.FilePicker(
   file_type=IMAGE, with_data=True)` opens the device camera for one photo
   on platforms that support it, or a plain file browser otherwise. The
   picked photo's bytes are decoded with `pyzbar` (native `libzbar`,
   installed in frontend/Dockerfile) - same deployment-safety reasoning as
   (2): only bytes the browser itself already delivered to Python are ever
   correct here.

Camera switching (front/rear/external, whenever more than one camera is
reported) matches senar's own `facingCamera` toggle UX
(`code/public/js/framework/y.form.js`'s `handleScanCamera()`), and a photo
picker is always offered alongside the live view regardless of whether a
camera was found - the one gap senar's own reference implementation never
handles (it just `console.error`s and stops with no camera).

Callers supply `on_scan(code: str)` and decide what a code means - this
component never resolves codes itself, regardless of which path produced the
code. For option-backed pickers, resolve via
`components/table/menu.py::resolve_option_value()` so the app keeps exactly
one matching rule (raw id / full label / `"{code} - {name}"` prefix, issue
#25); do not write a second matcher.
"""

import asyncio
import io
import time

import flet as ft
import flet_camera as fc
from PIL import Image, UnidentifiedImageError

try:
    import flet_permission_handler as fph
except ImportError:  # pragma: no cover - see _request_camera_permission
    fph = None

# Throttle for decoding frames off the live stream - `pyzbar` is a blocking
# call and a phone camera streams at ~15-30fps, so decoding every single
# frame would peg the CPU/battery for no benefit (a barcode sitting still in
# frame for even one decode attempt per few hundred ms is plenty responsive).
_STREAM_DECODE_INTERVAL_S = 0.4

# Ceiling on how long camera enumeration/initialize are allowed to hang
# before falling back to the existing error UI (issue #64 follow-up,
# 2026-07-30 - a real reported "sometimes freezes on first camera" with no
# prior timeout at all).
_CAMERA_INIT_TIMEOUT_S = 10.0

# Viewfinder reticle geometry (a camera reticle look - only the four
# corners are drawn, not a full border, per the requested UX) - centered
# over the full-screen camera feed (issue #64 follow-up, 2026-07-30: the
# camera view is now a full-screen borderless overlay, matching a
# conventional native QR/barcode scanner, rather than a small dialog box).
_VIEWFINDER_SQUARE = 220
_CORNER_SIZE = 28
_CORNER_THICKNESS = 4
_SCAN_LINE_ANIM_MS = 1400

# Translucent circular background for icon buttons floating directly over
# the live camera feed (close/switch-camera/gallery) - a plain IconButton
# with no background would be nearly invisible against a bright/busy
# camera image, and a solid opaque one would look out of place over a
# live video feed - matches the "usual" scanner-app look of dark
# semi-transparent circular controls overlaid on the viewfinder.
_OVERLAY_BUTTON_BG = ft.Colors.with_opacity(0.35, ft.Colors.BLACK)
_OVERLAY_BUTTON_ICON_COLOR = ft.Colors.WHITE


class ScanUnavailableError(RuntimeError):
    """Raised when `pyzbar` can't load the native `libzbar` shared library.

    `libzbar0` is only guaranteed present in the containerized deployment
    (installed explicitly in `frontend/Dockerfile`, issue #64) - a plain
    `flet run` outside Docker (e.g. issue #67's dev-mode test.ps1/test.sh
    options, or a native `flet build windows/macos/linux` desktop install)
    has no such guarantee. `pyzbar.pyzbar`'s import raises immediately if
    the shared library isn't found, so importing it at module level here
    would crash on load of THIS FILE - and this file is imported by nearly
    every form/table screen (via `components/form/input.py`), so that
    would break the entire app outside the container, not just the scan
    feature. Confirmed live: `flet run --web` on a bare Windows dev
    machine (no libzbar) failed to preload dozens of screens with a raw
    `FileNotFoundError: Could not find module 'libzbar-64.dll'` traceback
    before this fix. Importing lazily, only when a photo scan is actually
    attempted, contains the failure to just that one feature.
    """


def decode_image_bytes(data: bytes) -> str | None:
    """Decode the first barcode/QR found in raw image bytes, or `None` if
    none is found / the bytes aren't a decodable image. A thin wrapper
    around `pyzbar` so the dialog-building code below and any future
    non-UI caller (e.g. a test) share one decode path.

    Raises `ScanUnavailableError` if `pyzbar`/`libzbar` itself can't be
    loaded on this platform - see that class's docstring.
    """
    try:
        from pyzbar.pyzbar import decode as zbar_decode
    except (ImportError, OSError) as exc:
        raise ScanUnavailableError(
            f"Photo scanning is unavailable on this system (libzbar could "
            f"not be loaded: {exc})."
        ) from exc
    try:
        image = Image.open(io.BytesIO(data))
    except UnidentifiedImageError:
        return None
    results = zbar_decode(image)
    if not results:
        return None
    text = results[0].data.decode("utf-8", errors="replace")
    # Some symbologies embed a trailing CR/LF as an end-of-data marker (the
    # same character a hardware scanner's keyboard-wedge Enter represents) -
    # strip it so a decoded value never differs from what typing the same
    # code plus Enter into the manual field would have produced.
    return text.rstrip("\r\n")


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
        focus_next: ft.Control | None = None,
    ):
        self.page = page
        self.on_scan = on_scan
        self.title = title
        self.hint_text = hint_text
        self.tooltip = tooltip
        self.icon_size = icon_size
        self.width = width
        self.height = height
        # Optional "tab to next field" hook (per-request; a scanned code
        # can carry a trailing CR/LF the same way a hardware wedge's Enter
        # does, and a caller that knows its own next field can opt into
        # advancing focus there). `ScanInput` has no visibility into a
        # form's own field order, so this stays an explicit, per-instance
        # opt-in rather than an automatic DOM-tab-order guess (Flet has no
        # such concept to hook into anyway).
        self.focus_next = focus_next
        self.dialog: ft.AlertDialog | None = None
        self.field: ft.TextField | None = None
        self.error_text: ft.Text | None = None
        self.file_picker: ft.FilePicker | None = None

        # Live camera-scan state (issue #64 follow-up) - rebuilt fresh each
        # time the scan button opens, same "never reuse a stale control"
        # convention as `self.dialog`/`self.field` above. `camera_overlay`
        # is a full-screen `page.overlay` entry (NOT an `ft.AlertDialog` -
        # see `_open_camera()`'s own comment for why a real native-scanner
        # look needs a borderless full-screen container instead of dialog
        # chrome).
        self.camera: fc.Camera | None = None
        self.cameras: list[fc.CameraDescription] = []
        self.camera_index = 0
        self.camera_overlay: ft.Container | None = None
        self.camera_area: ft.Container | None = None
        self.camera_top_bar: ft.Row | None = None
        self.camera_bottom_bar: ft.Row | None = None
        self.camera_status: ft.Text | None = None
        self.scan_line: ft.Container | None = None
        self._last_decode_ts = 0.0
        self._scan_active = False
        self._scan_line_at_top = True

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

    # -------------------------------------------------------- entry point

    async def _open(self, e=None) -> None:
        """Primary click target: try a live camera scan first, falling back
        to the manual-entry dialog if no camera is found or anything about
        the camera path fails - never a dead end, matching issue #64's
        "never a silent failure" requirement one level up from the photo
        path's own existing retry-with-error behavior.
        """
        try:
            await self._open_camera()
        except Exception:
            self._open_manual()

    def _open_manual(self, e=None, error_text: str | None = None) -> None:
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
        # `.rstrip("\r\n")` defensively mirrors decode_image_bytes()'s own
        # stripping - a hardware wedge's terminating Enter shouldn't reach
        # `.value` at all (on_submit fires on the keypress itself), but a
        # pasted/typed value could still carry one.
        code = (self.field.value or "").rstrip("\r\n").strip() if self.field else ""
        self._close()
        if code and self.on_scan:
            self.on_scan(code)
            self._advance_focus()

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

    def _advance_focus(self) -> None:
        if self.focus_next is None:
            return
        try:
            self.focus_next.focus()
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
            # with no error, same as a plain Cancel. `_open_manual` (not
            # `_open`, which is async and re-attempts the live camera) -
            # a camera-scan detour that ended in "never mind, I'll type
            # it" shouldn't loop back into re-initializing the camera.
            self._open_manual()
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
            self._open_manual(error_text="Could not read the selected photo. Try again.")
            return

        try:
            code = decode_image_bytes(data)
        except ScanUnavailableError as exc:
            self._open_manual(error_text=str(exc))
            return
        if code:
            if self.on_scan:
                self.on_scan(code)
                self._advance_focus()
            return

        # "Never a silent failure" (issue #64 acceptance criteria) - reopen
        # the manual-entry dialog with an error and let the user retry the
        # photo (via its own "Choose from Gallery" button) or fall back to
        # hardware-scanner/typed entry.
        self._open_manual(
            error_text="No barcode/QR found in that photo. Try again or enter the code manually."
        )

    # ---------------------------------------------------------- live camera scan

    def _overlay_icon_button(self, icon, tooltip: str, on_click) -> ft.IconButton:
        """A translucent circular icon button meant to float directly over
        the live camera feed - see `_OVERLAY_BUTTON_BG`'s own comment for
        why a plain/opaque button doesn't work here."""
        return ft.IconButton(
            icon=icon,
            tooltip=tooltip,
            on_click=on_click,
            icon_color=_OVERLAY_BUTTON_ICON_COLOR,
            style=ft.ButtonStyle(
                bgcolor=_OVERLAY_BUTTON_BG,
                shape=ft.CircleBorder(),
            ),
        )

    async def _open_camera(self) -> None:
        # Full-screen, borderless overlay - a plain `page.overlay` entry
        # (same mechanism `components/loading_overlay.py` already uses
        # for a full-screen control, NOT an `ft.AlertDialog`), matching a
        # conventional native QR/barcode scanner app: the camera feed
        # fills the entire screen and every control (close, camera-switch,
        # gallery) floats directly on top of it, rather than sitting in a
        # small card with title/dialog chrome around a boxed-in preview
        # (issue #64 follow-up, 2026-07-30, explicit user request).
        self.cameras = []
        self.camera_index = 0
        self.camera = fc.Camera(expand=True, preview_enabled=True)
        self.camera.on_state_change = self._on_camera_state_change
        self.camera.on_stream_image = self._on_stream_image

        self.camera_status = ft.Text(
            "Starting camera...",
            size=13,
            color=ft.Colors.WHITE,
            text_align=ft.TextAlign.CENTER,
        )
        self.scan_line = ft.Container(
            width=_VIEWFINDER_SQUARE,
            height=2,
            bgcolor=ft.Colors.GREEN,
            left=0,
            top=0,
            animate_position=ft.Animation(_SCAN_LINE_ANIM_MS, ft.AnimationCurve.EASE_IN_OUT),
            # Drives the bounce loop off the client's own animation-complete
            # event instead of a Python `asyncio.sleep` guess - see
            # `_on_scan_line_animation_end()`'s own docstring for why the
            # previous sleep-loop was the actual source of the reported
            # "glitch/stutter", not just a timing constant to retune.
            on_animation_end=self._on_scan_line_animation_end,
        )
        viewfinder = ft.Stack(
            width=_VIEWFINDER_SQUARE,
            height=_VIEWFINDER_SQUARE,
            controls=[
                self.scan_line,
                self._corner_bracket(top=True, left=True),
                self._corner_bracket(top=True, left=False),
                self._corner_bracket(top=False, left=True),
                self._corner_bracket(top=False, left=False),
            ],
        )
        # While a camera is active/streaming, "Enter Manually" is
        # deliberately NOT offered here (explicit user request - a working
        # scanner doesn't need a manual-entry escape hatch the way the
        # no-camera/error fallback below still does); the close (X) button
        # is the only way out, same as backing out of any native scanner.
        self.camera_bottom_bar = ft.Row(
            controls=[
                self._overlay_icon_button(
                    ft.Icons.PHOTO_LIBRARY_OUTLINED, "Gallery", self._use_gallery_from_camera
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
        )
        self.camera_top_bar = ft.Row(
            controls=[
                self._overlay_icon_button(ft.Icons.CLOSE, "Close", self._cancel_camera),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.camera_area = ft.Container(
            expand=True,
            bgcolor=ft.Colors.BLACK,
            content=ft.Stack(
                expand=True,
                controls=[self.camera],
            ),
        )
        self.camera_overlay = ft.Container(
            expand=True,
            bgcolor=ft.Colors.BLACK,
            content=ft.Stack(
                expand=True,
                controls=[
                    self.camera_area,
                    # Centered reticle, floating over the full-bleed feed.
                    ft.Container(
                        alignment=ft.Alignment.CENTER,
                        expand=True,
                        content=viewfinder,
                    ),
                    # Top bar: close (left) + camera-switch (right, added
                    # once the camera count is known below) - floats over
                    # the feed rather than living in dialog chrome.
                    ft.Container(
                        top=0,
                        left=0,
                        right=0,
                        padding=ft.Padding.only(top=24, left=12, right=12),
                        content=self.camera_top_bar,
                    ),
                    # Bottom: status caption + Gallery, floating near the
                    # bottom edge of the feed.
                    ft.Container(
                        left=0,
                        right=0,
                        bottom=0,
                        padding=ft.Padding.only(bottom=32, left=16, right=16),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=16,
                            controls=[self.camera_status, self.camera_bottom_bar],
                        ),
                    ),
                ],
            ),
        )
        self.page.overlay.append(self.camera_overlay)
        self._safe_page_update()

        self._scan_active = True
        self._scan_line_at_top = True

        try:
            self.cameras = await asyncio.wait_for(
                self.camera.get_available_cameras(), timeout=_CAMERA_INIT_TIMEOUT_S
            )
        except (Exception, asyncio.TimeoutError):
            self.cameras = []

        if not self.cameras:
            self._show_no_camera()
            return

        # Prefer a rear/back-facing camera as the default - matches
        # senar's own default "environment" facing mode
        # (`handleScanCamera()`'s `facingCamera`).
        self.camera_index = next(
            (
                i
                for i, c in enumerate(self.cameras)
                if c.lens_direction == fc.CameraLensDirection.BACK
            ),
            0,
        )
        await self._request_camera_permission()

        # `asyncio.wait_for` guards against a real, reported failure mode
        # (issue #64 follow-up, 2026-07-30: "on first camera sometimes it
        # freezes") - `camera.initialize()` is a native plugin call with no
        # guaranteed return; without a timeout, a hang here left the
        # overlay stuck on "Starting camera..." forever with no way out
        # except the close button. A timeout instead surfaces the same
        # `_show_camera_error` fallback every other init failure already
        # uses, so the user always has Gallery/Enter Manually available.
        try:
            await asyncio.wait_for(
                self.camera.initialize(
                    description=self.cameras[self.camera_index],
                    resolution_preset=fc.ResolutionPreset.MEDIUM,
                    enable_audio=False,
                    image_format_group=fc.ImageFormatGroup.JPEG,
                ),
                timeout=_CAMERA_INIT_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            self._show_camera_error("timed out starting the camera")
            return
        except Exception as exc:
            self._show_camera_error(str(exc))
            return

        # Camera-switch button, floated top-right - always added whenever
        # more than one camera is available (explicit user request: this
        # is a required control on the live-scan screen, not an
        # afterthought), inserted once the real camera count is known
        # (same timing as before - right after a successful initialize).
        if len(self.cameras) > 1:
            self.camera_top_bar.controls.append(
                self._overlay_icon_button(
                    ft.Icons.CAMERASWITCH_OUTLINED, "Switch camera", self._switch_camera
                )
            )

        try:
            supported = await self.camera.supports_image_streaming()
        except Exception:
            supported = False

        if supported:
            try:
                await self.camera.start_image_stream()
                self.camera_status.value = "Point the camera at a barcode or QR code"
            except Exception as exc:
                self._show_camera_error(str(exc))
                return
        else:
            self.camera_status.value = (
                "Live scanning isn't supported on this camera - use Gallery"
            )

        self._safe_page_update()
        # Kicks off the scan-line bounce loop - `animate_position` only
        # interpolates a CHANGE, so the line mounts motionless at top=0
        # until this first flip actually triggers a transition; every
        # further flip is then driven by `_on_scan_line_animation_end`
        # firing when the client reports that transition genuinely
        # finished, not by a Python-side timer guess.
        self._on_scan_line_animation_end()

    def _corner_bracket(self, top: bool, left: bool) -> ft.Container:
        # A camera-reticle look - only the two edges of one corner are
        # drawn, not a full square border, per the requested UX.
        side = ft.BorderSide(_CORNER_THICKNESS, ft.Colors.GREEN)
        border = ft.Border(
            top=side if top else None,
            bottom=None if top else side,
            left=side if left else None,
            right=None if left else side,
        )
        return ft.Container(
            width=_CORNER_SIZE,
            height=_CORNER_SIZE,
            border=border,
            left=0 if left else None,
            right=None if left else 0,
            top=0 if top else None,
            bottom=None if top else 0,
        )

    def _on_scan_line_animation_end(self, e=None) -> None:
        # Replaces an earlier `asyncio.sleep`-driven bounce loop (issue #64
        # follow-up, 2026-07-30) that was reported as "a little glitch,
        # stop, or not smooth" even after moving the blocking `pyzbar`
        # decode off the event loop. Root cause: a fixed-duration
        # `asyncio.sleep(_SCAN_LINE_ANIM_MS / 1000)` assumes Python's own
        # timer fires in lockstep with the CLIENT's actual Flutter-side
        # `animate_position` transition - any event-loop scheduling jitter
        # (a `page.update()` round trip taking a little longer some ticks,
        # a stream-image callback landing at an inconvenient moment, ...)
        # desyncs the two, which reads as the line stuttering/stalling.
        # `on_animation_end` is a real, native Flutter event fired when a
        # transition actually finishes on the client - flipping the
        # position from THIS callback (self-correcting, driven by the
        # client's own report of completion) can't drift out of sync with
        # the visible animation, regardless of any Python-side timing
        # jitter.
        if not self._scan_active or self.scan_line is None:
            return
        self._scan_line_at_top = not self._scan_line_at_top
        self.scan_line.top = 0 if self._scan_line_at_top else (_VIEWFINDER_SQUARE - 2)
        self._safe_page_update()

    async def _request_camera_permission(self) -> None:
        # Native Android/iOS need an explicit runtime grant before the
        # camera plugin can open a stream; a browser's own getUserMedia
        # prompt already covers the web deployment (this app's primary
        # deployment target), where flet-permission-handler may not even
        # apply - best-effort either way, since a denial/absence still
        # surfaces naturally as a camera init error handled by
        # `_show_camera_error` below, not a crash here.
        if fph is None or self.page.web:
            return
        try:
            handler = fph.PermissionHandler()
            if handler not in self.page.services:
                self.page.services.append(handler)
            await handler.request(fph.Permission.CAMERA)
        except Exception:
            pass

    def _add_manual_entry_fallback(self) -> None:
        """Only the no-camera/error fallback offers "Enter Manually" -
        while a camera is actively streaming it's deliberately absent (see
        `_open_camera()`'s own comment), but once there's genuinely no
        working camera, typing the code is the only real alternative to
        Gallery, same as before this redesign."""
        if self.camera_bottom_bar is None:
            return
        already_present = any(
            getattr(c, "tooltip", None) == "Enter Manually"
            for c in self.camera_bottom_bar.controls
        )
        if not already_present:
            self.camera_bottom_bar.controls.insert(
                0,
                self._overlay_icon_button(
                    ft.Icons.KEYBOARD, "Enter Manually", self._use_manual_from_camera
                ),
            )

    def _show_no_camera(self) -> None:
        if self.camera_area is not None:
            self.camera_area.content = ft.Container(
                alignment=ft.Alignment.CENTER,
                expand=True,
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            ft.Icons.NO_PHOTOGRAPHY_OUTLINED,
                            color=ft.Colors.WHITE70,
                            size=48,
                        ),
                        ft.Text("No camera detected", color=ft.Colors.WHITE70, size=12),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
            )
        self._add_manual_entry_fallback()
        if self.camera_status is not None:
            self.camera_status.value = "Use Gallery or enter the code manually"
        self._scan_active = False
        self._safe_page_update()

    def _show_camera_error(self, message: str) -> None:
        self._add_manual_entry_fallback()
        if self.camera_status is not None:
            self.camera_status.value = f"Camera unavailable: {message}"
            self.camera_status.color = ft.Colors.ERROR
        self._scan_active = False
        self._safe_page_update()

    def _on_camera_state_change(self, e: fc.CameraStateEvent) -> None:
        if getattr(e, "has_error", False):
            self._show_camera_error(e.error_description or "unknown error")

    def _on_stream_image(self, e: fc.CameraImageEvent) -> None:
        # Sync handler (matches flet-camera's own documented pattern,
        # `preview.on_stream_image = on_stream_image`), throttled so it
        # only runs a few times a second instead of on every single
        # streamed frame (~15-30fps). The actual decode is dispatched to
        # `_decode_and_handle` below rather than called directly here -
        # see that method's own docstring for why (issue #64 follow-up,
        # 2026-07-30: real-device testing found the scan-line animation
        # "too fast or stuck" and the camera occasionally freezing on
        # first open, both traced to this handler blocking the event loop).
        if not self._scan_active:
            return
        now = time.monotonic()
        if now - self._last_decode_ts < _STREAM_DECODE_INTERVAL_S:
            return
        self._last_decode_ts = now
        self.page.run_task(self._decode_and_handle, e.bytes)

    async def _decode_and_handle(self, data: bytes) -> None:
        # `pyzbar` decode is a genuinely blocking call - previously invoked
        # directly inside the sync `_on_stream_image` handler above, which
        # runs on the same single-threaded asyncio event loop as every
        # other scheduled callback (including, at the time, a sleep-driven
        # scan-line bounce loop - since replaced by
        # `_on_scan_line_animation_end`'s client-event-driven flip, see its
        # own docstring). Every decode (up to twice a second per the
        # throttle) stalled that loop for its own duration - reported live
        # (2026-07-30) as the animation looking "too fast" (several delayed
        # updates catching up at once) or "stuck" (blocked mid-decode).
        # Running the decode in a worker thread via `asyncio.to_thread`
        # keeps the event loop free regardless of how long any single
        # decode takes.
        try:
            code = await asyncio.to_thread(decode_image_bytes, data)
        except ScanUnavailableError:
            return
        if code:
            await self._handle_scanned_code(code)

    async def _handle_scanned_code(self, code: str) -> None:
        if not self._scan_active:
            # Already handled by a previous frame's decode racing this one,
            # or the overlay was closed in the meantime.
            return
        self._scan_active = False
        await self._teardown_camera()
        if self.on_scan:
            self.on_scan(code)
            self._advance_focus()

    async def _switch_camera(self, e=None) -> None:
        if not self.cameras or self.camera is None:
            return
        self.camera_index = (self.camera_index + 1) % len(self.cameras)
        try:
            await self.camera.stop_image_stream()
        except Exception:
            pass
        try:
            await self.camera.initialize(
                description=self.cameras[self.camera_index],
                resolution_preset=fc.ResolutionPreset.MEDIUM,
                enable_audio=False,
                image_format_group=fc.ImageFormatGroup.JPEG,
            )
            if await self.camera.supports_image_streaming():
                await self.camera.start_image_stream()
        except Exception as exc:
            self._show_camera_error(str(exc))

    async def _use_manual_from_camera(self, e=None) -> None:
        self._scan_active = False
        await self._teardown_camera()
        self._open_manual()

    async def _use_gallery_from_camera(self, e=None) -> None:
        self._scan_active = False
        await self._teardown_camera()
        await self._pick_photo()

    async def _cancel_camera(self, e=None) -> None:
        self._scan_active = False
        await self._teardown_camera()

    async def _teardown_camera(self) -> None:
        # `_scan_active = False` (already set by every caller before this
        # runs) is enough to stop `_on_scan_line_animation_end` from
        # scheduling any further flips - no separate future/task to cancel
        # now that the bounce loop is driven by the client's own animation
        # events rather than a Python asyncio task.
        if self.camera is not None:
            try:
                await self.camera.stop_image_stream()
            except Exception:
                pass
        if self.camera_overlay is not None:
            try:
                self.page.overlay.remove(self.camera_overlay)
            except ValueError:
                pass
            self.camera_overlay = None
            self._safe_page_update()
