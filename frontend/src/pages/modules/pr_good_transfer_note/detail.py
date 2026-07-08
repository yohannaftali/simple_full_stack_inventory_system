import flet as ft

from components.module.view import ModuleView
from utils.http_client import HttpClient


class ModulePage:
    """Page 2 — PR detail + per-item picking modal (#628)."""

    def __init__(self, page: ft.Page, module: str, screen: str, record_id: str = None):
        self.page = page
        self.module = module
        self.screen = screen
        self.record_id = record_id
        self.header = {}
        self.items = []
        self._search = ""
        self._items_col = ft.Column([], spacing=0)
        self.view = ModuleView(page, module, screen)
        self.content = ft.Container(padding=0, expand=True)

    def build(self):
        self._load_data()
        self.content.content = self._build_content()
        return self.view.build(self.content, padding=0)

    def _load_data(self):
        client = HttpClient(self.page)
        response = client.get(f"C_{self.module}/get_stock_picking_detail?request_header_id={self.record_id}")
        if isinstance(response, dict) and "error" not in response:
            self.header = response.get("header", {}) or {}
            self.items = response.get("items", []) or []
        else:
            self.header, self.items = {}, []

    def _build_content(self):
        header_rows = [
            ("PR No", self.header.get("request_no", "-")),
            ("Department", self.header.get("department_name", "-")),
            ("Remark", self.header.get("remarks", "-")),
            ("User", self.header.get("user_name", "-")),
        ]
        header_card = ft.Container(
            content=ft.Column(
                [ft.Row([ft.Text(l, weight="bold", width=110), ft.Text(str(v or "-"), expand=True)], spacing=8)
                 for l, v in header_rows],
                spacing=6,
            ),
            padding=15,
        )

        search_bar = ft.TextField(
            hint_text="Search item name...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search_change,
            dense=True,
        )

        self._refresh_items_col()

        return ft.Column(
            [header_card, ft.Divider(),
             ft.Container(search_bar, padding=ft.Padding.symmetric(horizontal=12, vertical=6)),
             self._items_col],
            spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
        )

    def _on_search_change(self, e):
        self._search = e.control.value or ""
        self._refresh_items_col()
        self.page.update()

    def _refresh_items_col(self):
        q = self._search.lower()
        filtered = [it for it in self.items
                    if q in (it.get("description_item") or "").lower()] if q else self.items
        controls = [self._item_card(it) for it in filtered]
        self._items_col.controls = controls or [ft.Container(ft.Text("No items."), padding=15)]

    def _item_card(self, item):
        req = self._num(item.get("qty_request"))
        pick = self._num(item.get("qty_picking"))
        remaining = self._num(item.get("qty_remaining"))
        subtitle = ft.Column(
            [
                ft.Text(item.get("detail_item", "") or "", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(f"Material: {item.get('material_name', '') or '-'}", size=12),
                ft.Text(f"Request: {req:g}   Picking: {pick:g}   Remaining: {remaining:g}", size=12,
                        weight=ft.FontWeight.W_500),
            ],
            spacing=2,
        )
        return ft.Card(
            content=ft.ListTile(
                title=ft.Text(item.get("description_item", "") or "-", weight=ft.FontWeight.W_600),
                subtitle=subtitle,
                trailing=ft.Icon(ft.Icons.EDIT_NOTE),
                on_click=lambda e, it=item: self._open_pick_modal(it),
            ),
        )

    def _open_pick_modal(self, item):
        req = self._num(item.get("qty_request"))
        remaining = self._num(item.get("qty_remaining"))
        qty_field = ft.TextField(label="Qty", keyboard_type=ft.KeyboardType.NUMBER, autofocus=True)

        def on_submit(e):
            try:
                qty = float(qty_field.value)
            except (TypeError, ValueError):
                self._snack("Enter a valid quantity")
                return
            if qty <= 0:
                self._snack("Qty must be greater than 0")
                return
            if qty > remaining:
                self._snack(f"Qty exceeds remaining ({remaining:g})")
                return
            self._submit_pick(item, qty)

        modal = ft.AlertDialog(
            title=ft.Text(item.get("description_item", "") or "Pick Item"),
            content=ft.Column(
                [
                    ft.Text(f"Qty Request: {req:g}"),
                    ft.Text(f"Qty Remaining: {remaining:g}", weight=ft.FontWeight.W_600),
                    qty_field,
                ],
                spacing=10, width=350, tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_modal()),
                ft.Button("Submit", on_click=on_submit),
            ],
        )
        self.page.overlay.append(modal)
        modal.open = True
        self.page.update()

    def _submit_pick(self, item, qty):
        client = HttpClient(self.page)
        payload = {
            "request_header_id": self.record_id,
            "request_item_id": item.get("request_item_id"),
            "material_id": item.get("material_id"),
            "qty": qty,
        }
        response = client.post(f"C_{self.module}/submit_stock_picking", data=payload)

        if isinstance(response, dict) and response.get("success"):
            self._close_modal()
            self._snack("Picking saved")
            self._load_data()
            # Auto-hide: all items fulfilled -> back to the PR list.
            if all(self._num(it.get("qty_remaining")) <= 0 for it in self.items):
                self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")
                return
            self.content.content = self._build_content()
            self.page.update()
        else:
            msg = response.get("error", "Failed to save") if isinstance(response, dict) else "Failed to save"
            self._snack(msg)

    def _close_modal(self):
        for control in self.page.overlay:
            if isinstance(control, ft.AlertDialog):
                control.open = False
        self.page.update()

    def _snack(self, message: str):
        snack = ft.SnackBar(ft.Text(message))
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    @staticmethod
    def _num(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
