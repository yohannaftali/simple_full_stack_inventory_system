import flet as ft

from components.module.view import ModuleView
from components.module.view_toggle import ViewToggle


class ModulePage:
    """Module page class"""

    def __init__(self, page: ft.Page, module: str, screen=str):
        self.page = page
        self.module = module
        self.screen = screen

        self.fields = [
            {
                "name": "id",
                "type": "hidden", "key": True, "serialize": False
            },
            {
                "name": "date", "label": "Date",
                "type": "label", "format": "date", "sort": True, "filter": True,
                "position": "leading", "row": 0
            },
            {
                "name": "description", "label": "Description",
                "type": "label", "sort": True, "filter": True,
                "position": "title", "row": 0
            },
            {
                "name": "supplier_name", "label": "Supplier",
                "type": "label", "sort": True, "filter": True,
                "position": "subtitle", "row": 0
            }
        ]

        self.view = ModuleView(page, module, screen)

        # Table/List view toggle (issue #56) - the same "detail" endpoint/
        # fields render as either a List (default) or a Table, switched via
        # a toolbar button, with the free-text search term carried across
        # the switch (see components/module/view_toggle.py's docstring for
        # the full design and its documented sort/pagination scope limit).
        self.toggle = ViewToggle(
            page=page,
            parent=self,
            name="detail",
            fields=self.fields,
            list_kwargs={"leading": {"width": 90}},
        )
        self.toggle.add_new_button(callback=self.callback_add_new)

    def build(self):
        return self.view.build(self.body(), padding=0)

    def body(self):
        return self.toggle.build()

    def callback_add_new(self, e):
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/new")
