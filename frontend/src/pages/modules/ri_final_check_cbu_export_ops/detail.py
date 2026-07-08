import flet as ft

from components.module.view import ModuleView
from utils.http_client import HttpClient


class ModulePage:
    """Vehicle detail page for Final Inspection"""

    def __init__(self, page: ft.Page, module: str, screen: str, record_id: str = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id
        self.vehicle_data = {}
        self.pic_options = []
        self.view = ModuleView(page, module, screen)

    def build(self):
        """Build and return the page"""
        self._load_vehicle_data()
        self._load_pic_options()
        return self.view.build(self._build_content())

    def _build_content(self):
        """Build the main content"""
        # Vehicle master data display
        data_rows = [
            ("Model", self.vehicle_data.get('model', '-')),
            ("Model Code", self.vehicle_data.get('model_code', '-')),
            ("Chassis No", self.vehicle_data.get('chassis_no', '-')),
            ("Engine No", self.vehicle_data.get('engine_no', '-')),
            ("Color", self.vehicle_data.get('color', '-')),
            ("Country", self.vehicle_data.get('country', '-')),
            ("Line", self.vehicle_data.get('line_no', '-')),
            ("Status", self.vehicle_data.get('status', '-')),
        ]

        data_content = ft.Column([
            ft.Row([
                ft.Text(label, weight="bold", width=100),
                ft.Text(str(value), expand=True),
            ], spacing=10)
            for label, value in data_rows
        ], spacing=8)

        return ft.Column([
            ft.Container(content=data_content, padding=15, expand=True),
            ft.Divider(),
            ft.Container(
                content=ft.Row([
                    ft.Button(
                        "Pending",
                        icon=ft.Icons.ACCESS_TIME_FILLED,
                        on_click=self.on_pending_click,
                        expand=True,
                        bgcolor=ft.Colors.AMBER_500,
                        color=ft.Colors.WHITE,
                    ),
                    ft.Button(
                        "Confirm",
                        icon=ft.Icons.CHECK_CIRCLE,
                        on_click=self.on_confirm_click,
                        expand=True,
                        bgcolor=ft.Colors.GREEN_500,
                        color=ft.Colors.WHITE,
                    ),
                ], spacing=10, expand=True),
                padding=10,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

    def _load_vehicle_data(self):
        """Load vehicle data from backend"""
        try:
            client = HttpClient(self.page)
            response = client.get(f'C_ri_final_check_cbu_export_ops/get?inspection_detail_id={self.record_id}')
            if isinstance(response, dict) and 'master' in response:
                self.vehicle_data = response['master']
                print(f"Loaded vehicle data: {self.vehicle_data}")
        except Exception as e:
            print(f"Error loading vehicle data: {e}")

    def _load_pic_options(self):
        """Load PIC options from backend"""
        try:
            client = HttpClient(self.page)
            response = client.get('C_ri_final_check_cbu_export_ops/call_cu_username_select')
            print(f"PIC response: {response}")
            if isinstance(response, list):
                self.pic_options = response
        except Exception as e:
            print(f"Error loading PIC options: {e}")

    def on_pending_click(self, e):
        print("Pending button clicked")
        self.show_pending_modal()

    def on_confirm_click(self, e):
        print("Confirm button clicked")
        self.show_confirm_modal()

    def show_pending_modal(self):
        """Show pending modal"""
        print("Opening pending modal")

        pic_dropdown = ft.Dropdown(
            label="Select PIC",
            options=[
                ft.dropdown.Option(text=opt.get('label', opt.get('value', '')),
                                 key=opt.get('value', ''))
                for opt in self.pic_options
            ],
            expand=True,
        )

        remark_field = ft.TextField(
            label="Remark",
            multiline=True,
            min_lines=3,
        )

        def on_submit(e):
            if not pic_dropdown.value:
                self._show_snackbar("Please select a PIC")
                return
            self._submit_pending(pic_dropdown.value, remark_field.value)

        modal = ft.AlertDialog(
            title=ft.Text("Mark as Pending"),
            content=ft.Column([
                pic_dropdown,
                remark_field,
            ], spacing=10, width=350),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_modal()),
                ft.Button("Submit", on_click=on_submit),
            ],
        )

        self.page.overlay.append(modal)
        modal.open = True
        self.page.update()
        print("Pending modal opened")

    def show_confirm_modal(self):
        """Show confirm modal"""
        print("Opening confirm modal")

        pic_dropdown = ft.Dropdown(
            label="Select PIC",
            options=[
                ft.dropdown.Option(text=opt.get('label', opt.get('value', '')),
                                 key=opt.get('value', ''))
                for opt in self.pic_options
            ],
            expand=True,
        )

        def on_submit(e):
            if not pic_dropdown.value:
                self._show_snackbar("Please select a PIC")
                return
            self._submit_confirm(pic_dropdown.value)

        modal = ft.AlertDialog(
            title=ft.Text("Confirm Inspection"),
            content=ft.Column([
                pic_dropdown,
            ], spacing=10, width=350),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_modal()),
                ft.Button("Confirm", on_click=on_submit),
            ],
        )

        self.page.overlay.append(modal)
        modal.open = True
        self.page.update()
        print("Confirm modal opened")

    def _submit_pending(self, pic_username: str, remark: str):
        """Submit pending action"""
        try:
            print(f"Submitting pending: {pic_username}, {remark}")
            client = HttpClient(self.page)
            payload = {
                'inspection_detail_id': self.record_id,
                'cu_username': pic_username,
                'cu_remark': remark,
            }
            response = client.post('C_ri_final_check_cbu_export_ops/pending', data=payload)
            print(f"Pending response: {response}")
            if isinstance(response, dict) and response.get('success'):
                self._close_modal()
                self._show_snackbar("Inspection marked as pending")
                self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")
            else:
                error_msg = response.get('error', 'Failed to submit') if isinstance(response, dict) else 'Failed to submit'
                self._show_snackbar(error_msg)
        except Exception as e:
            print(f"Pending error: {e}")
            self._show_snackbar(f"Error: {str(e)}")

    def _submit_confirm(self, pic_username: str):
        """Submit confirm action"""
        try:
            print(f"Submitting confirm: {pic_username}")
            client = HttpClient(self.page)
            payload = {
                'inspection_detail_id': self.record_id,
                'cu_username': pic_username,
            }
            response = client.post('C_ri_final_check_cbu_export_ops/confirm', data=payload)
            print(f"Confirm response: {response}")
            if isinstance(response, dict) and response.get('success'):
                self._close_modal()
                self._show_snackbar("Inspection confirmed successfully")
                self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")
            else:
                error_msg = response.get('error', 'Failed to confirm') if isinstance(response, dict) else 'Failed to confirm'
                self._show_snackbar(error_msg)
        except Exception as e:
            print(f"Confirm error: {e}")
            self._show_snackbar(f"Error: {str(e)}")

    def _close_modal(self):
        """Close current modal"""
        # Close any open dialogs in overlay
        for control in self.page.overlay:
            if isinstance(control, ft.AlertDialog):
                control.open = False
        self.page.update()

    def _show_snackbar(self, message: str):
        """Show snackbar message"""
        snack = ft.SnackBar(ft.Text(message))
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()
