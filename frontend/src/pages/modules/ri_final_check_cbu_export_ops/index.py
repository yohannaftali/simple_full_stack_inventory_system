import flet as ft

from components.module.view import ModuleView
from components.list.list import List


class ModulePage:
    """VIN List page for Final Inspection module"""

    def __init__(self, page: ft.Page, module: str, screen: str):
        self.page = page
        self.module = module
        self.screen = screen

        self.fields = [
            {
                "name": "inspection_detail_id",
                "type": "hidden"
            },
            {
                "name": "model_code",
                "position": "leading"
            },
            {
                "name": "color",
                "position": "leading"
            },
            {
                "name": "chassis_no",
                "position": "title"
            },
            {
                "name": "engine_no",
                "position": "subtitle"
            },
        ]

        self.list = List(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields,
            endpoint="C_ri_final_check_cbu_export_ops/get_detail",
            is_inside_form=True  # Don't auto-load on init, only after search
        )

        # Override tiles load to add click navigation
        self._original_tiles_load = self.list.tiles.load
        self.list.tiles.load = self._custom_tiles_load

        self.view = ModuleView(page, module, screen)

    def _custom_tiles_load(self, data: list, append: bool = False):
        """Custom tiles load that makes tiles clickable for navigation"""
        # Call original load first
        self._original_tiles_load(data, append)

        # Add click handler to each tile for navigation to detail
        for i, tile in enumerate(self.list.tiles.tiles):
            if i < len(data):
                record = data[i] if not append else data[i - (len(self.list.tiles.tiles) - len(data))]
                detail_id = record.get("inspection_detail_id", "")

                # Make tile clickable
                tile.on_click = lambda e, did=detail_id: self.page.run_task(self.page.push_route, f"/modules/{self.module}/detail/{did}")

    def build(self):
        return self.view.build(self.body())

    def body(self):
        return self.list.build()
