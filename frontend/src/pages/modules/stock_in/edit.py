import flet as ft

from components.module.view import ModuleView
from components.form.form import Form
from pages.modules.stock_in.item_table import ItemTable


class ModulePage:
    """Module screen class"""

    def __init__(self, page: ft.Page, module: str, screen=str, record_id: str | int = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id

        self.fields = [
            {
                "name": "id", "type": "hidden",
                "key": True,
            },
            {
                "name": "date", "label": "Date", "icon": ft.Icons.EVENT,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "date", "autofocus": True
            },
            {
                "name": "supplier_id", "label": "Supplier", "icon": ft.Icons.LOCAL_SHIPPING,
                "row": 1, "col": {"sm": 12, "md": 6},
                "type": "select"
            },
            {
                "name": "description", "label": "Description", "icon": ft.Icons.NOTES,
                "row": 2,
                "type": "input"
            }
        ]

        self.form = Form(
            page=page,
            parent=self,
            name="edit",
            fields=self.fields
        )

        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Edit Receiving")

        # Must come after self.view is assigned - ItemTable/Table fetch data
        # immediately and reach back through parent.view.show_error() on
        # failure.
        self.item_table = ItemTable(page, self, module, record_id)

        self.view.toolbar.add_submit_button(callback=self.callback_submit)

    def build(self):
        return self.view.build(self.body())

    def body(self):
        return ft.Column(
            controls=[
                self.form.build(),
                # Table's internal layout expands to fill its parent, which
                # needs a bounded height when nested alongside other content
                # in a scrolling Column - otherwise it collapses to zero
                # height instead of rendering its own internal scroll region.
                ft.Container(content=self.item_table.build(), height=400),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def callback_submit(self, e):
        self.form.submit()
