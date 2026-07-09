"""Inventory value repository — read access only.

Writes are owned by `services.inventory_service`, which manages its own
transaction spanning receiving/stock/inventory-value together (see that
module's docstring for why).
"""

from typing import Optional

from models.base import SessionLocal
from models.inventory_value import InventoryValueModel


class InventoryValueRepository:
    """Repository class for inventory valuation read access."""

    def get_by_material_id(self, material_id: int) -> Optional[InventoryValueModel]:
        with SessionLocal() as session:
            return (
                session.query(InventoryValueModel)
                .filter(InventoryValueModel.material_id == material_id)
                .first()
            )

    def get_all(self) -> list[InventoryValueModel]:
        with SessionLocal() as session:
            return session.query(InventoryValueModel).all()
