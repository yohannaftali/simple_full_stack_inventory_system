"""Stock in / stock out business logic: keeps `receiving_items`, `stocks`, and
`inventory_values` (moving average price) consistent, and `stock_out_items` /
`stocks` consistent on issue.

Deliberately bypasses the repository layer for its writes and manages one
`SessionLocal()` transaction per operation directly, because a single
"receive" or "issue" call must touch multiple tables atomically — something
the rest of the codebase's one-repository-method-per-table-per-session
pattern isn't set up for. Reads elsewhere in the app still go through the
repositories.

Moving average price (MAP): for material with `qty` on hand at `average_price`,
receiving `new_qty` at `new_price` recomputes as a weighted average:
    new_average_price = (qty * average_price + new_qty * new_price) / (qty + new_qty)
Issuing stock decreases `qty` but never changes `average_price` (standard
moving-average costing). Editing an existing receiving item's qty/price is
handled by first reversing its old contribution (subtracting old_qty/old_price
from the running qty/cost) then applying the new one — this is exact *as long
as no stock-out for that material happened between the original receipt and
the edit*; the service does not replay full transaction history, so an edit
to an old receipt with intervening issues will only approximately correct the
average. Acceptable simplification for a "simple" inventory system; a real
lot-costing ledger would be needed to do this perfectly.
"""

from decimal import Decimal, InvalidOperation

from models.base import SessionLocal
from models.inventory_value import InventoryValueModel
from models.location import LocationModel
from models.material import MaterialModel
from models.receiving_item import ReceivingItemModel
from models.stock import StockModel
from models.stock_out_item import StockOutItemModel
from services.bulk_service import BulkRowError


class InsufficientStockError(Exception):
    """Raised when a stock-out would take a material+location below zero."""

    def __init__(self, available: Decimal):
        self.available = available
        super().__init__(f"Insufficient stock: only {available} available")


def _get_or_create_inventory_value(session, material_id: int) -> InventoryValueModel:
    inv = (
        session.query(InventoryValueModel)
        .filter(InventoryValueModel.material_id == material_id)
        .first()
    )
    if inv is None:
        inv = InventoryValueModel(material_id=material_id, qty=Decimal("0"), average_price=Decimal("0"))
        session.add(inv)
        session.flush()
    return inv


def _apply_receiving_delta(
    inv: InventoryValueModel,
    old_qty: Decimal,
    old_price: Decimal,
    new_qty: Decimal,
    new_price: Decimal,
) -> None:
    """Reverse the old (qty, price) contribution and apply the new one."""
    base_qty = inv.qty - old_qty
    base_cost = (inv.qty * inv.average_price) - (old_qty * old_price)

    total_qty = base_qty + new_qty
    total_cost = base_cost + (new_qty * new_price)

    inv.qty = total_qty
    inv.average_price = (total_cost / total_qty) if total_qty > 0 else Decimal("0")


def create_receiving_item(
    receiving_header_id: int,
    material_id: int,
    location_id: int,
    price_buy: Decimal,
    qty_received: Decimal,
    remarks: str,
) -> ReceivingItemModel:
    """Create a receiving item, its stock lot, and update the material's MAP."""
    with SessionLocal() as session:
        item = ReceivingItemModel(
            receiving_header_id=receiving_header_id,
            material_id=material_id,
            location_id=location_id,
            price_buy=price_buy,
            qty_received=qty_received,
            remarks=remarks,
        )
        session.add(item)
        session.flush()

        session.add(
            StockModel(
                receiving_item_id=item.id,
                material_id=material_id,
                location_id=location_id,
                qty=qty_received,
            )
        )

        inv = _get_or_create_inventory_value(session, material_id)
        _apply_receiving_delta(inv, Decimal("0"), Decimal("0"), qty_received, price_buy)

        session.commit()
        session.refresh(item)
        return item


def create_receiving_items_bulk(receiving_header_id: int, rows: list[dict]) -> dict:
    """ALL OR NOTHING bulk version of `create_receiving_item` (issue #24) -
    same convention as `services/bulk_service.py::bulk_create`, but that
    helper's single `session.add(build_instance(row, session))` shape
    doesn't fit here: one receiving item is three co-dependent writes
    (`ReceivingItemModel` + `StockModel` + the material's `InventoryValueModel`
    MAP update), not one. Owns its own `SessionLocal()` for the whole batch,
    flushing after each row's writes (surfacing FK/constraint errors
    attributed to that row) and committing once only if every row succeeds.

    Each row applies its MAP contribution against whatever `InventoryValueModel`
    state the *previous* row in this same batch already flushed - identical
    sequencing to calling `create_receiving_item` once per row, just inside
    one transaction instead of one per call.
    """
    if not rows:
        return {"error": "No rows to import"}

    with SessionLocal() as session:
        current_row = rows[0]["_row"]
        try:
            for row in rows:
                current_row = row["_row"]

                material_raw = str(row.get("material_id", "")).strip()
                location_raw = str(row.get("location_id", "")).strip()
                if not material_raw or not location_raw:
                    raise BulkRowError(current_row, "Material and Location are required")
                try:
                    material_id = int(material_raw)
                    location_id = int(location_raw)
                except ValueError:
                    raise BulkRowError(current_row, "Invalid Material or Location")

                try:
                    qty_received = Decimal(str(row.get("qty_received", "")).strip())
                except InvalidOperation:
                    raise BulkRowError(
                        current_row, f"Invalid quantity: {row.get('qty_received', '')}"
                    )
                if qty_received <= 0:
                    raise BulkRowError(current_row, "Quantity received must be greater than zero")

                price_raw = str(row.get("price_buy", "")).strip()
                try:
                    price_buy = Decimal(price_raw) if price_raw else Decimal("0")
                except InvalidOperation:
                    raise BulkRowError(current_row, f"Invalid price: {price_raw}")
                if price_buy < 0:
                    raise BulkRowError(current_row, "Price cannot be negative")

                material = session.get(MaterialModel, material_id)
                if material is None:
                    raise BulkRowError(current_row, f"Unknown material id {material_id}")
                if not material.is_active:
                    raise BulkRowError(current_row, "Cannot receive: material is inactive")

                if session.get(LocationModel, location_id) is None:
                    raise BulkRowError(current_row, f"Unknown location id {location_id}")

                item = ReceivingItemModel(
                    receiving_header_id=receiving_header_id,
                    material_id=material_id,
                    location_id=location_id,
                    price_buy=price_buy,
                    qty_received=qty_received,
                    remarks=str(row.get("remarks", "")).strip(),
                )
                session.add(item)
                session.flush()

                session.add(
                    StockModel(
                        receiving_item_id=item.id,
                        material_id=material_id,
                        location_id=location_id,
                        qty=qty_received,
                    )
                )

                inv = _get_or_create_inventory_value(session, material_id)
                _apply_receiving_delta(inv, Decimal("0"), Decimal("0"), qty_received, price_buy)
                session.flush()

            session.commit()
        except BulkRowError as e:
            session.rollback()
            return {"error": f"Row {e.row_number}: {e.message}"}

    return {"message": f"{len(rows)} item(s) added"}


def update_receiving_item(
    item_id: int,
    price_buy: Decimal,
    qty_received: Decimal,
    remarks: str,
) -> ReceivingItemModel | None:
    """Update a receiving item's qty/price/remarks (material/location are fixed).

    Recomputes the material's stock lot and MAP by reversing the item's old
    contribution and applying the new one.
    """
    with SessionLocal() as session:
        item = (
            session.query(ReceivingItemModel).filter(ReceivingItemModel.id == item_id).first()
        )
        if item is None:
            return None

        old_qty = item.qty_received
        old_price = item.price_buy

        item.price_buy = price_buy
        item.qty_received = qty_received
        item.remarks = remarks

        stock = (
            session.query(StockModel)
            .filter(StockModel.receiving_item_id == item_id)
            .first()
        )
        if stock is not None:
            stock.qty = qty_received

        inv = _get_or_create_inventory_value(session, item.material_id)
        _apply_receiving_delta(inv, old_qty, old_price, qty_received, price_buy)

        session.commit()
        session.refresh(item)
        return item


def create_stock_out_item(
    stock_out_header_id: int,
    material_id: int,
    location_id: int,
    qty_out: Decimal,
    remarks: str,
) -> StockOutItemModel:
    """Issue stock: deduct FIFO from the material's lots at `location_id`,
    capture the material's current MAP as the issue price, decrement the
    material's total qty (price unchanged), and record the stock out item.

    Raises InsufficientStockError if the location doesn't have enough.
    """
    with SessionLocal() as session:
        lots = (
            session.query(StockModel)
            .filter(StockModel.material_id == material_id, StockModel.location_id == location_id)
            .order_by(StockModel.id)
            .all()
        )
        available = sum((lot.qty for lot in lots), Decimal("0"))
        if available < qty_out:
            raise InsufficientStockError(available)

        remaining = qty_out
        for lot in lots:
            if remaining <= 0:
                break
            deduct = min(lot.qty, remaining)
            lot.qty -= deduct
            remaining -= deduct

        inv = _get_or_create_inventory_value(session, material_id)
        price = inv.average_price
        inv.qty = inv.qty - qty_out

        stock_out_item = StockOutItemModel(
            stock_out_header_id=stock_out_header_id,
            material_id=material_id,
            location_id=location_id,
            qty_out=qty_out,
            price=price,
            total_value=qty_out * price,
            remarks=remarks,
        )
        session.add(stock_out_item)

        session.commit()
        session.refresh(stock_out_item)
        return stock_out_item
