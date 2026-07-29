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
            {"name": "id", "type": "hidden", "key": True, "serialize": False},
            {
                # Icon instead of a text label on the leading position
                # (issue #65) - matches senar's own List convention
                # (confirmed directly against real consumers in
                # C:\Users\IT\Git\senar\flet\senar\src\pages\modules\
                # pm_data_cbu_inbound/ri_receiving\index.py: a leading date
                # field gets "icon": ft.Icons.DATE_RANGE, never a "label").
                # Table tolerates a missing "label" gracefully too
                # (TableColumns._build_data_columns() already falls back to
                # icon-only when label is None), so the same shared fields
                # list still works for the Table view (issue #56's
                # ViewToggle) - the Date column header becomes a calendar
                # icon instead of the text "Date".
                "name": "date",
                "label": "Date",
                "icon": ft.Icons.CALENDAR_TODAY,
                "type": "label",
                "format": "date",
                "sort": True,
                "filter": True,
                "position": "leading",
                "row": 0,
            },
            {
                "name": "supplier_name",
                "label": "Supplier",
                "type": "label",
                "sort": True,
                "filter": True,
                "position": "title",
                "row": 0,
            },
            {
                "name": "description",
                "label": "Description",
                "type": "label",
                "sort": True,
                "filter": True,
                "position": "subtitle",
                "row": 0,
            },
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
