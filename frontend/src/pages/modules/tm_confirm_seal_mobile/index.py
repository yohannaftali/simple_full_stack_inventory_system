import flet as ft

from components.module.view import ModuleView
from components.list.list import List


class ModulePage:
    """Module page class for TM Confirm Seal Mobile - Trip List"""

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
            # {
            #     "name": "driver_name",
            #     "icon": ft.Icons.PERSON,
            #     "position": "leading", "row": 0
            # },
            # {
            #     "name": "equipment_license_no",
            #     "position": "leading", "row": 1
            # },
            {
                "name": "driver_name_license_no",
                "position": "subtitle", "row": 0
            },
            # {
            #     "name": "dn_no_trip",
            #     "position": "subtitle", "row": 0
            # },
        ]

        self.view = ModuleView(page, module, screen)

        self.list = List(
            page=page,
            parent=self,
            name="trip_list",
            fields=self.fields
        )

        # Store original load method and override with custom one
        self._original_tiles_load = self.list.tiles.load
        self.list.tiles.load = self._custom_tiles_load

    def _custom_tiles_load(self, data: list, append: bool = False):
        self._original_tiles_load(data, append)

        tiles = self.list.tiles.tiles
        
        if append:
            start_index = len(tiles) - len(data)
            for i, record in enumerate(data):
                tile_index = start_index + i
                if tile_index < len(tiles):
                    trip_actual_id = record.get("trip_actual_id", "")
                    tiles[tile_index].on_click = lambda e, tid=trip_actual_id: self.page.run_task(self.page.push_route, 
                        f"/modules/{self.module}/scan/{tid}")
        else:
            for i, record in enumerate(data):
                if i < len(tiles):
                    trip_actual_id = record.get("trip_actual_id", "")
                    tiles[i].on_click = lambda e, tid=trip_actual_id: self.page.run_task(self.page.push_route, 
                        f"/modules/{self.module}/scan/{tid}")

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.list.build()
