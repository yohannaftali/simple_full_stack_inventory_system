import flet as ft

from components.module.view import ModuleView
from components.form.form import Form
from components.form.input import InputForm
from components.form.button import ButtonForm
from components.form.label import LabelForm
from utils.http_client import HttpClient


class ModulePage:
    """Module page class for TM Confirm Seal Mobile - Scan Segel"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        self.view = ModuleView(page, module, screen)

        self.seal_inputs = {}
        self.seal_fields_column = ft.Column(
            controls=[],
            spacing=8,
        )


        # Trip data from tm_data_trip_pu
        self.trip_data = {}

        # Trip actual data
        self.trip_actual_data = {}
        self._load_trip_actual_data()

        # Trip info display default
        self.trip_info_column = ft.Column(
            controls=[
                ft.Text(
                    f"No. Surat Tugas: {self.trip_actual_data.get('no_surat_tugas', '-')}",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    f"Driver: {self.trip_actual_data.get('driver_name', '-')}",
                    size=13,
                ),
                ft.Text(
                    f"No. Pol: {self.trip_actual_data.get('equipment_license_no', '-')}",
                    size=13,
                ),
                ft.Divider(height=10),
                # ft.Text(
                #     "Segel Asal:",
                #     size=12,
                #     color=ft.Colors.ON_SURFACE_VARIANT,
                # ),
                # ft.Text(
                #     "-",
                #     size=14,
                #     weight=ft.FontWeight.BOLD,
                #     color=ft.Colors.PRIMARY,
                #     selectable=True,
                # ),
            ],
            spacing=3,
        )

        self.fields = [
             {
                "name": "no_surat_jalan",
                "type": "input",
                "label": "No. Surat Jalan",
                "icon": ft.Icons.DESCRIPTION,
                "hint_text": "Masukkan No. Surat Jalan",
                "autofocus": True,
                "row": 0,
            },
            {
                "name": "seal_fields",
                "type": "custom",
                "control": self.seal_fields_column,
                "row": 1,
            },
            {
                "name": "remarks",
                "type": "input",
                "label": "Remarks",
                "icon": ft.Icons.NOTE,
                "multiline": True,
                "min_lines": 2,
                "max_lines": 3,
                "row": 2,
            },
            {
                "name": "btn_cancel",
                "type": "button",
                "label": "Cancel",
                "icon": ft.Icons.CANCEL,
                "bgcolor": ft.Colors.RED,
                "color": ft.Colors.ON_SURFACE,
                "on_click": self._on_cancel,
                "row": 2,
                "col": {"xs": 6},
            },
            {
                "name": "btn_submit",
                "type": "button",
                "label": "Submit",
                "icon": ft.Icons.CHECK,
                "bgcolor": ft.Colors.GREEN,
                "color": ft.Colors.ON_SURFACE,
                "on_click": self._on_submit,
                "row": 2,
                "col": {"xs": 6},
            },
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="scan_form",
            fields=self.fields,
            endpoint_submit=f"C_{self.module}/submit_seal",
            start_blank=True,
        )

        self._setup_custom_handlers()

        # self.scan_progress = ft.Text("0/5 segel", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

    def _load_trip_actual_data(self):
        """Load trip actual data from API based on trip_actual_id"""
        if not self.record_id:
            return

        client = HttpClient(self.page)
        response = client.get(
            f"C_{self.module}/get_trip_detail?trip_actual_id={self.record_id}")

        if isinstance(response, dict) and "error" not in response:
            self.trip_actual_data = response

            if response.get("no_surat_jalan") and response.get("no_surat_jalan") != "-":
                self._loaded_no_surat_jalan = response.get("no_surat_jalan")
                self.trip_data = response

    def _on_surat_jalan_submit(self, e):
        """Fetch trip data from tm_data_trip_pu based on no_surat_jalan"""
        surat_jalan_input = self.form.elements.get("no_surat_jalan")
        no_surat_jalan = (surat_jalan_input.value if surat_jalan_input else "") or ""
        no_surat_jalan = no_surat_jalan.strip()
        
        if not no_surat_jalan:
            self._update_trip_info_display({})
            return

        client = HttpClient(self.page)
        response = client.get(
            f"C_{self.module}/get_trip_by_surat_jalan?no_surat_jalan={no_surat_jalan}")

        if isinstance(response, dict) and "error" not in response and response:
            self.trip_data = response
            self._update_trip_info_display(response)
            equipment_type_id = str(response.get("equipment_type_id", ""))
            self._build_seal_fields(equipment_type_id)
        else:
            self.trip_data = {}
            self.seal_inputs = {}
            self.seal_fields_column.controls.clear()
            self.seal_fields_column.update()
            error_msg = response.get("error", "No. Surat Jalan tidak ditemukan") if isinstance(response, dict) else "No. Surat Jalan tidak ditemukan"
            self._update_trip_info_display({}, error_msg)

    def _update_trip_info_display(self, data: dict, error: str = None):
        self.trip_info_column.controls.clear()
        
        if error:
            self.trip_info_column.controls.append(
                ft.Text(error, size=13, color=ft.Colors.ERROR)
            )
        else:
            self.trip_info_column.controls.extend([
                ft.Text(
                    f"No. Surat Tugas: {self.trip_actual_data.get('no_surat_tugas', '-')}",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    f"Driver: {self.trip_actual_data.get('driver_name', '-')}",
                    size=13,
                ),
                ft.Text(
                    f"No. Pol: {self.trip_actual_data.get('equipment_license_no', '-')}",
                    size=13,
                ),
                ft.Divider(height=10),
                # ft.Text(
                #     "Segel Asal:",
                #     size=12,
                #     color=ft.Colors.ON_SURFACE_VARIANT,
                # ),
                # ft.Text(
                #     f"{data.get('seal_from', '-')}",
                #     size=14,
                #     weight=ft.FontWeight.BOLD,
                #     color=ft.Colors.PRIMARY,
                #     selectable=True,
                # ),
            ])
        
        self.trip_info_column.update()

    def _setup_custom_handlers(self):
        """Set up custom handlers for form inputs"""
        # Wire on_submit and on_blur for no_surat_jalan
        surat_jalan_input = self.form.elements.get("no_surat_jalan")
        if isinstance(surat_jalan_input, ft.TextField):
            surat_jalan_input.on_submit = self._on_surat_jalan_submit
            surat_jalan_input.on_blur = self._on_surat_jalan_submit
            # Set pre-loaded value if available
            if hasattr(self, '_loaded_no_surat_jalan'):
                surat_jalan_input.value = self._loaded_no_surat_jalan

    SEAL_LABELS = {
        "7": [  # Tronton
            "Kanan Depan",
            "Kanan Belakang",
            "Kiri Depan",
            "Kiri Belakang",
            "Tengah Belakang",
        ],
        "5": [  # Engkel
            "Kanan",
            "Kiri",
            "Tengah",
        ],
    }

    def _build_seal_fields(self, equipment_type_id: str):
        labels = self.SEAL_LABELS.get(equipment_type_id, [])
        self.seal_inputs = {}
        self.seal_fields_column.controls.clear()

        if not labels:
            self.seal_fields_column.update()
            return

        type_name = "Tronton" if equipment_type_id == "7" else "Engkel"
        self.seal_fields_column.controls.append(
            ft.Text(
                f"Scan Segel Tujuan ({type_name} - {len(labels)} segel)",
                size=14,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.PRIMARY,
            )
        )

        seal_keys = []
        for i, label in enumerate(labels, start=1):
            key = f"seal_{i}"
            seal_keys.append(key)
            tf = ft.TextField(
                label=f"{i}. {label}",
                prefix_icon=ft.Icons.VERIFIED_USER,
                hint_text=f"Scan segel {label.lower()}",
                border_radius=10,
                text_size=16,
                autofocus=(i == 1),
            )
            self.seal_inputs[key] = tf
            self.seal_fields_column.controls.append(tf)

        for idx, key in enumerate(seal_keys):
            next_key = seal_keys[idx + 1] if idx + 1 < len(seal_keys) else None
            self.seal_inputs[key].on_submit = self._make_seal_next_focus(next_key)

        self.seal_fields_column.update()

    def _make_seal_next_focus(self, next_key):
        def handler(e):
            if next_key and next_key in self.seal_inputs:
                self.page.run_task(self.seal_inputs[next_key].focus)
        return handler


    def _on_submit(self, e):
        if not self.trip_data:
            self.view.show_error("Data trip belum dimuat. Masukkan No. Surat Jalan terlebih dahulu.")
            return

        no_surat_tugas = self.trip_actual_data.get("no_surat_tugas", "")
        if not no_surat_tugas:
            self.view.show_error("No. Surat Tugas tidak ditemukan")
            return

        if not self.seal_inputs:
            self.view.show_error("Kolom segel tujuan belum muncul. Masukkan No. Surat Jalan terlebih dahulu.")
            return

        empty_fields = []
        for key, tf in self.seal_inputs.items():
            val = (tf.value or "").strip()
            if not val:
                empty_fields.append(tf.label)
        
        if empty_fields:
            self.view.show_error(f"Segel belum diisi: {', '.join(empty_fields)}")
            return

        self._do_submit()

    # def _show_confirm_dialog(self, scan_count: int, seal_from_count: int, seal_destination: str):
    #     def on_confirm(e):
    #         dialog.open = False
    #         self.page.update()
    #         self._do_submit(seal_destination)

    #     def on_cancel(e):
    #         dialog.open = False
    #         self.page.update()

    #     dialog = ft.AlertDialog(
    #         modal=True,
    #         title=ft.Text("Konfirmasi"),
    #         content=ft.Text(
    #             f"Anda hanya scan {scan_count} segel dari {seal_from_count} segel asal.\n\n"
    #             f"Apakah Anda yakin ingin submit {scan_count} segel?",
    #             size=14,
    #         ),
    #         actions=[
    #             ft.TextButton("Batal", on_click=on_cancel),
    #             ft.TextButton("Ya, Submit", on_click=on_confirm),
    #         ],
    #         actions_alignment=ft.MainAxisAlignment.END,
    #     )
    #     self.page.overlay.append(dialog)
    #     dialog.open = True
    #     self.page.update()

    def _do_submit(self):
        """Actually submit the data to API"""
        no_surat_jalan = self.trip_data.get("no_surat_jalan", "")
        no_surat_tugas = self.trip_actual_data.get("no_surat_tugas", "")
        remarks_input = self.form.elements.get("remarks")
        
        data = {
            "no_surat_jalan": no_surat_jalan,
            "no_surat_tugas": no_surat_tugas,
            "remarks": remarks_input.value if remarks_input else "",
        }

        for key, tf in self.seal_inputs.items():
            data[key] = (tf.value or "").strip()

        client = HttpClient(self.page)
        response = client.post(f"C_{self.module}/submit_seal", data)

        if isinstance(response, dict):
            if "error" in response:
                error_msg = response.get("error", "Unknown error")
                # if "seal_from" in response and "seal_destination" in response:
                #     error_msg += f"\n\nSegel Asal: {response.get('seal_from')}\nSegel Tujuan: {response.get('seal_destination')}"
                self.view.show_error(error_msg)
            elif "success" in response:
                self.view.show_success(response.get("success", "Success"))
                self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")
        else:
            self.view.show_error("Unexpected response from server")

    def _on_cancel(self, e):
        """Handle cancel button click"""
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body(), padding=10)

    def body(self):
        """Build the scan form body"""

        def show_info_dialog(e):
            dialog = ft.AlertDialog(
                title=ft.Text("Petunjuk Scan Segel", weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    controls=[
                        ft.Text("Mohon scan segel sesuai urutan berikut:", size=14),
                        ft.Divider(height=10),
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(
                                        "Tipe Tronton\n1. Kanan Depan\n2. Kanan Belakang\n3. Kiri Depan\n4. Kiri Belakang\n5. Tengah Belakang",
                                        size=13,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        "Tipe Engkel\n1. Kanan\n2. Kiri\n3. Tengah",
                                        size=13,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            spacing=15,
                        ),
                    ],
                    tight=True,
                    spacing=5,
                ),
                actions=[
                    ft.TextButton("Tutup", on_click=lambda e: self._close_dialog(dialog)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.overlay.append(dialog)
            dialog.open = True
            self.page.update()

        header_row = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=self.trip_info_column,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.INFO_OUTLINE,
                            icon_size=30,
                            icon_color=ft.Colors.PRIMARY,
                            on_click=show_info_dialog,
                            tooltip="Petunjuk Scan",
                        ),
                        alignment=ft.Alignment.TOP_CENTER,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.Padding.all(12),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=8,
            margin=ft.Margin.only(bottom=10),
            expand=True,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    header_row,
                    self.form.build(padding=0),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=ft.Padding.all(15),
            margin=ft.Margin.symmetric(vertical=8),
            expand=True,
        )

    def _close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

