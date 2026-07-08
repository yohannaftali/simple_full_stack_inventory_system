import flet as ft

from components.module.view import ModuleView
from components.list.list import List
from utils.http_client import HttpClient


class ModulePage:
    """Module page class"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        """
        Initialize Module Page

        Args:
            page: The Flet page
            module: string
            screen: string
            record_id: string | int
        """
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        self.fields = [
            {
                "name": "inspection_header_id",
                "type": "hidden"
            },
            {
                "name": "date", "icon": ft.Icons.DATE_RANGE,
                "position": "leading", "row": 0
            },
            {
                "name": "shift_name",
                "position": "leading", "row": 1
            },
            {
                "name": "reference",
                "position": "title"
            },
            {
                "name": "remarks",
                "position": "subtitle", "row": 0
            },
        ]

        self.view = ModuleView(page, module, screen)

        self.list = List(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields
        )

        # Store original load method and override with custom one
        self._original_tiles_load = self.list.tiles.load
        self.list.tiles.load = self._custom_tiles_load

        # self.list.toolbar.add_button(
        #     position="right",
        #     icon=ft.Icons.REFRESH,
        #     tooltip="Refresh",
        #     callback=self.callback_refresh
        # )

        self._add_shift_toolbar()

    def _add_shift_toolbar(self):
        shift_data = self._get_current_shift()
        shift_name = shift_data.get("shift_name", "No Shift Selected")

        shift_button = ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ACCESS_TIME, color=ft.Colors.ON_PRIMARY_CONTAINER, size=18),
                    ft.Text(shift_name, color=ft.Colors.ON_PRIMARY_CONTAINER, weight=ft.FontWeight.W_500),
                ],
                spacing=5,
            ),
            tooltip="Change Shift",
            on_click=self._on_shift_click
        )

        self.list.toolbar.right = self.list.toolbar.right or []
        self.list.toolbar.right.insert(0, shift_button)

    def _get_current_shift(self):
        client = HttpClient(self.page)
        response = client.get("C_home/call_get_current_shift")

        if isinstance(response, dict) and "error" not in response:
            return response
        return {"shift_id": "", "shift_name": "No Shift Selected"}

    def _on_shift_click(self, e):
        """Navigate to shift modal"""
        self.page.run_task(self.page.push_route, "/modals/shift/index")

    def _custom_tiles_load(self, data: list, append: bool = False):
        """Custom tiles load that adds navigation trailing button"""
        # Call original load first
        self._original_tiles_load(data, append)
        
        # Add trailing button to each tile for navigation to detail
        for i, tile in enumerate(self.list.tiles.tiles):
            if i < len(data):
                record = data[i] if not append else data[i - (len(self.list.tiles.tiles) - len(data))]
                header_id = record.get("inspection_header_id", "")
                
                # Add trailing icon button for navigation
                tile.trailing = ft.IconButton(
                    icon=ft.Icons.ARROW_FORWARD_IOS,
                    icon_size=16,
                    tooltip="View Details",
                    on_click=lambda e, hid=header_id: self.page.run_task(self.page.push_route, f"/modules/{self.module}/detail/{hid}")
                )

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.list.build()

    def on_sort(self, e):
        print(f"{e.column_index}, {e.ascending}")

    # def callback_refresh(self, e):
    #     endpoint = f"C_{self.module}/refresh_data"
    #     self.view.try_get(endpoint)
    #     print("refresh")
