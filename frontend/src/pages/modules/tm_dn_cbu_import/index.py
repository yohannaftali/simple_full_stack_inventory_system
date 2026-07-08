import flet as ft

from components.module.view import ModuleView
from components.list.list import List


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
                "name": "trip_actual_id",
                "type": "hidden"
            },
            {
                "name": "no_surat_tugas",
                "position": "title"
            },
            {
                "name": "datetime_assigned", "icon": ft.Icons.DATE_RANGE,
                "position": "leading", "row": 0
            }
        ]

        # is_inside_form=True prevents auto-load on init; data loads only after search
        self.list = List(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields,
            is_inside_form=True
        )

        # Override get_data: only fetch when search filter is set
        self._original_get_data = self.list.get_data
        self.list.get_data = self._guarded_get_data

        # Override tile load: set on_click on each row to navigate to edit
        self._original_tiles_load = self.list.tiles.load
        self.list.tiles.load = self._custom_tiles_load

        self.view = ModuleView(page, module, screen)

    def _guarded_get_data(self, page_no=1, offset=0, append=False):
        """Only load data when a search filter is set"""
        if not self.list.filter:
            # Clear existing tiles when filter is cleared
            self.list.tiles.tiles = []
            if self.list.body and self.list.body.list_view:
                self.list.body.list_view.controls = []
                self.list.body.list_view.update()
            return
        self._original_get_data(page_no, offset, append)

    def _custom_tiles_load(self, data: list, append: bool = False):
        """Custom tile load: whole row navigates directly to edit"""
        self._original_tiles_load(data, append)

        start = len(self.list.tiles.tiles) - len(data) if append else 0
        for i, tile in enumerate(self.list.tiles.tiles[start:], start=start):
            if i - start < len(data):
                record = data[i - start]
                trip_id = record.get("trip_actual_id", "")

                tile.on_click = lambda e, tid=trip_id: self.page.run_task(self.page.push_route, 
                    f"/modules/{self.module}/edit/{tid}"
                )

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.list.build()
