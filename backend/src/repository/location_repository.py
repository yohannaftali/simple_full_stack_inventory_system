"""Location repository for data access operations."""

from typing import Optional

from sqlalchemy import func, or_

from models.base import SessionLocal
from models.location import LocationModel


class LocationRepository:
    """Repository class for location data access operations."""

    def get_location_by_id(self, location_id: int) -> Optional[LocationModel]:
        with SessionLocal() as session:
            return session.query(LocationModel).filter(LocationModel.id == location_id).first()

    def get_location_by_code(self, code: str) -> Optional[LocationModel]:
        with SessionLocal() as session:
            return session.query(LocationModel).filter(LocationModel.code == code).first()

    def get_all_locations(self) -> list[LocationModel]:
        with SessionLocal() as session:
            return session.query(LocationModel).order_by(LocationModel.code).all()

    def list_locations(
        self, keyword: str = "", limit: int = 20, offset: int = 0
    ) -> tuple[list[LocationModel], int]:
        with SessionLocal() as session:
            query = session.query(LocationModel)
            if keyword:
                like = f"%{keyword}%"
                query = query.filter(
                    or_(LocationModel.code.like(like), LocationModel.name.like(like))
                )
            total = query.with_entities(func.count(LocationModel.id)).scalar() or 0
            rows = query.order_by(LocationModel.code).offset(offset).limit(limit).all()
            return rows, total

    def create_location(self, code: str, name: str) -> LocationModel:
        with SessionLocal() as session:
            location = LocationModel(code=code, name=name)
            session.add(location)
            session.commit()
            session.refresh(location)
            return location

    def update_location(self, location_id: int, code: str, name: str) -> bool:
        with SessionLocal() as session:
            location = (
                session.query(LocationModel).filter(LocationModel.id == location_id).first()
            )
            if location is None:
                return False

            location.code = code
            location.name = name
            session.commit()
            return True

    def delete_location(self, location_id: int) -> bool:
        with SessionLocal() as session:
            location = (
                session.query(LocationModel).filter(LocationModel.id == location_id).first()
            )
            if location is None:
                return False

            session.delete(location)
            session.commit()
            return True
