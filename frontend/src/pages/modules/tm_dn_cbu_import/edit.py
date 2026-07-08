import flet as ft

from components.module.view import ModuleView
from utils.http_client import HttpClient


class ModulePage:
    """Module page for inputting VIN list against a Surat Tugas (trip_actual)"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        """
        Initialize Module Page

        Args:
            page: The Flet page
            module: string
            screen: string
            record_id: trip_actual_id
        """
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        # Load data first to determine page mode
        self.trip_data = self._load_trip_data()
        self.submitted_vins = self._load_submitted_vins()
        self.is_submitted = len(self.submitted_vins) > 0

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("CBU Import")
        self.view.header.on_click = self._on_back_click

        # Submit button only available when not yet submitted; Print button in view mode
        if not self.is_submitted:
            self.view.toolbar.add_submit_button(callback=self._callback_submit)
        else:
            self.view.toolbar.add_button(
                position="right",
                icon=ft.Icons.PRINT,
                tooltip="Print Surat Jalan",
                callback=self._callback_print,
            )

        # VIN input fields only needed in edit mode
        self.vin_fields: list[ft.TextField] = []
        self.vin_column = ft.Column(spacing=8, controls=[])

        if not self.is_submitted:
            self._add_vin_row()

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------

    def _load_trip_data(self) -> dict:
        """Fetch single trip_actual record for the header card"""
        client = HttpClient(self.page)
        response = client.get(
            f"C_{self.module}/get",
            {"trip_actual_id": self.record_id}
        )
        if isinstance(response, dict) and "error" not in response:
            return response.get("master", response)
        return {}

    def _load_submitted_vins(self) -> list:
        """Fetch VINs already assigned to this trip_actual_id"""
        client = HttpClient(self.page)
        response = client.get(
            f"C_{self.module}/get_vins",
            {"trip_actual_id": self.record_id}
        )
        if isinstance(response, list):
            return response
        return []

    # -------------------------------------------------------------------------
    # VIN row management (edit mode only)
    # -------------------------------------------------------------------------

    def _add_vin_row(self, e=None):
        """Append a new VIN input row to the column"""
        tf = ft.TextField(
            hint_text="Scan / Input VIN",
            expand=True,
            autofocus=True,
            border_radius=8,
            text_size=14,
            on_submit=lambda ev: self._add_vin_row(),
        )

        remove_btn = ft.IconButton(
            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
            icon_color=ft.Colors.ERROR,
            icon_size=22,
            tooltip="Hapus baris",
            visible=False,
            on_click=lambda ev, field=tf: self._remove_vin_row(field),
        )

        row_ctrl = ft.Row(
            controls=[tf, remove_btn],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.vin_fields.append(tf)
        self.vin_column.controls.append(row_ctrl)
        self._refresh_remove_visibility()

        # Flet 0.85's Control.page property raises RuntimeError (instead of
        # returning None) when the control hasn't been mounted yet.
        try:
            mounted = self.vin_column.page is not None
        except RuntimeError:
            mounted = False
        if mounted:
            self.vin_column.update()

    def _remove_vin_row(self, tf: ft.TextField):
        """Remove the row that contains the given TextField"""
        idx = self.vin_fields.index(tf)
        self.vin_fields.pop(idx)
        self.vin_column.controls.pop(idx)
        self._refresh_remove_visibility()
        self.vin_column.update()

    def _refresh_remove_visibility(self):
        """Show remove button only when there are 2+ rows"""
        visible = len(self.vin_fields) > 1
        for row_ctrl in self.vin_column.controls:
            if isinstance(row_ctrl, ft.Row) and len(row_ctrl.controls) >= 2:
                row_ctrl.controls[-1].visible = visible

    # -------------------------------------------------------------------------
    # Build
    # -------------------------------------------------------------------------

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    self._build_header_card(),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "List VIN No." if self.is_submitted else "Input VIN",
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                self._build_vin_section(),
                            ],
                            spacing=10,
                        ),
                        padding=ft.Padding(left=16, right=16, top=12, bottom=24),
                    ),
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            expand=True,
        )

    def _build_vin_section(self):
        """Route to view-only or editable VIN section based on submission status"""
        if self.is_submitted:
            return self._build_submitted_vins()
        return self._build_editable_vins()

    def _build_submitted_vins(self):
        """View-only list of already submitted VINs"""
        tiles = []
        for record in self.submitted_vins:
            vin = record.get("item_name", "-")
            tiles.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=18),
                            ft.Text(vin, size=14),
                        ],
                        spacing=8,
                    ),
                    padding=ft.Padding(left=4, right=4, top=6, bottom=6),
                )
            )
        return ft.Column(controls=tiles, spacing=2)

    def _build_editable_vins(self):
        """Editable VIN input column with add button"""
        return ft.Column(
            controls=[
                self.vin_column,
                ft.OutlinedButton(
                    icon=ft.Icons.ADD,
                    content="Tambah VIN",
                    on_click=self._add_vin_row,
                ),
            ],
            spacing=10,
        )

    def _build_header_card(self):
        """Read-only card showing Surat Tugas info"""
        no_st     = self.trip_data.get("no_surat_tugas", "-")
        route     = self.trip_data.get("route", "-")
        driver    = self.trip_data.get("driver_name", "-")
        co_driver = self.trip_data.get("co_driver_name", "-")
        equipment = self.trip_data.get("equipment_license_no", "-")

        def _info_row(icon, label, value):
            return ft.Row(
                controls=[
                    ft.Icon(icon, size=15, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(
                        f"{label}:",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        width=72,
                    ),
                    ft.Text(str(value) if value else "-", size=12, expand=True),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.ASSIGNMENT_OUTLINED, color=ft.Colors.PRIMARY),
                        title=ft.Text(no_st, weight=ft.FontWeight.W_600, size=14),
                        subtitle=ft.Text(str(route), size=12),
                        dense=True,
                    ),
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                _info_row(ft.Icons.PERSON, "Driver", driver),
                                _info_row(ft.Icons.PERSON_OUTLINE, "Co-Driver", co_driver),
                                _info_row(ft.Icons.LOCAL_SHIPPING, "No. Polisi", equipment),
                            ],
                            spacing=6,
                        ),
                        padding=ft.Padding(left=16, right=16, top=4, bottom=10),
                    ),
                ],
                spacing=0,
            ),
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            border_radius=8,
            margin=ft.Margin(left=10, right=10, top=12, bottom=0),
        )

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def _callback_print(self, e):
        """Generate PDF surat jalan and open in device browser"""
        client = HttpClient(self.page)
        response = client.get(
            f"C_{self.module}/get_surat_jalan",
            {"trip_actual_id": self.record_id}
        )
        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return
        url = response.get("url", "") if isinstance(response, dict) else ""
        if url:
            self.page.launch_url(url)

    def _on_back_click(self, e):
        """Navigate back to index"""
        if hasattr(self.page, "banner") and self.page.banner:
            self.page.banner.open = False
            self.page.update()
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")

    # -------------------------------------------------------------------------
    # Submit
    # -------------------------------------------------------------------------

    def _callback_submit(self, e):
        """Validate each VIN one by one, then submit if all pass"""
        vins = [tf.value.strip() for tf in self.vin_fields if tf.value and tf.value.strip()]

        if not vins:
            self.view.show_error("Minimal 1 VIN harus diisi")
            return

        client = HttpClient(self.page)
        invalid_vins: list[str] = []

        for vin in vins:
            response = client.post(
                f"C_{self.module}/validate_vin",
                data={"vin_no": vin}
            )
            if isinstance(response, dict) and "error" in response:
                invalid_vins.append(vin)

        if invalid_vins:
            self.view.show_error(
                f"VIN tidak ditemukan: {', '.join(invalid_vins)}"
            )
            return

        submit_data: dict = {"trip_actual_id": self.record_id}
        for i, vin in enumerate(vins):
            submit_data[f"vin_list[{i}]"] = vin

        response = client.post(f"C_{self.module}/submit", data=submit_data)

        if isinstance(response, dict) and "error" in response:
            self.view.show_error(response["error"])
            return

        message = "Berhasil disimpan"
        if isinstance(response, dict):
            message = response.get("message", response.get("msg", message))

        if self.page.overlay:
            self.page.overlay[0].visible = True
            self.page.update()

        new_page = self.__class__(self.page, self.module, self.screen, self.record_id)
        self.page.views[-1] = new_page.build()

        if self.page.overlay:
            self.page.overlay[0].visible = False
        self.view.show_success(message)
