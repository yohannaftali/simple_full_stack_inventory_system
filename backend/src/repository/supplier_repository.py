"""Supplier repository for data access operations."""

from typing import Optional

from core.table_query import Pagination, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.supplier import SupplierModel


class SupplierRepository:
    """Repository class for supplier data access operations."""

    def get_supplier_by_id(self, supplier_id: int) -> Optional[SupplierModel]:
        with SessionLocal() as session:
            return session.query(SupplierModel).filter(SupplierModel.id == supplier_id).first()

    def get_supplier_by_code(self, code: str) -> Optional[SupplierModel]:
        with SessionLocal() as session:
            return session.query(SupplierModel).filter(SupplierModel.code == code).first()

    def get_all_suppliers(self) -> list[SupplierModel]:
        with SessionLocal() as session:
            return session.query(SupplierModel).order_by(SupplierModel.code).all()

    def list_suppliers(
        self, keyword: str = "", limit: int = 20, page: int = 1, offset: int = 0
    ) -> tuple[list[SupplierModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(SupplierModel)
            query = apply_keyword_filter(
                query, [SupplierModel.code, SupplierModel.name], keyword
            )
            query = query.order_by(SupplierModel.code)
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_supplier(self, code: str, name: str) -> SupplierModel:
        with SessionLocal() as session:
            supplier = SupplierModel(code=code, name=name)
            session.add(supplier)
            session.commit()
            session.refresh(supplier)
            return supplier

    def update_supplier(self, supplier_id: int, code: str, name: str) -> bool:
        with SessionLocal() as session:
            supplier = (
                session.query(SupplierModel).filter(SupplierModel.id == supplier_id).first()
            )
            if supplier is None:
                return False

            supplier.code = code
            supplier.name = name
            session.commit()
            return True

    def delete_supplier(self, supplier_id: int) -> bool:
        with SessionLocal() as session:
            supplier = (
                session.query(SupplierModel).filter(SupplierModel.id == supplier_id).first()
            )
            if supplier is None:
                return False

            session.delete(supplier)
            session.commit()
            return True
