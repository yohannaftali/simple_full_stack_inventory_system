"""Location master-data CRUD admin screen (frontend module `master_location`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_location")`.
"""

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.exc import IntegrityError

from core.table_query import attach_pagination, parse_sort_fields
from models.location import LocationModel
from models.user import UserModel
from repository.location_repository import LocationRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_master_location", tags=["master-location"])
_location_repository = LocationRepository()

_require_access = require_module_access("master_location")


def _serialize(location: LocationModel) -> dict:
    return {"id": location.id, "code": location.code, "name": location.name}


@router.get("/get_detail")
def get_detail(
    request: Request,
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    sort_fields = parse_sort_fields(request.query_params)
    rows, pagination = _location_repository.list_locations(
        keyword=keyword, limit=limit, page=page, offset=offset, sort_fields=sort_fields
    )
    return attach_pagination([_serialize(location) for location in rows], pagination)


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    location = _location_repository.get_location_by_id(id)
    if location is None:
        return {"error": "Location not found"}
    return _serialize(location)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    code: str = Form(...),
    name: str = Form(...),
    user: UserModel = Depends(_require_access),
) -> dict:
    if id:
        updated = _location_repository.update_location(int(id), code=code, name=name)
        if not updated:
            return {"error": "Location not found"}
        return {"message": "Location updated successfully"}

    _location_repository.create_location(code=code, name=name)
    return {"message": "Location created successfully"}


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    try:
        deleted = _location_repository.delete_location(int(id))
    except IntegrityError:
        return {"error": "Cannot delete: this location has receiving/stock/issue history"}
    if not deleted:
        return {"error": "Location not found"}
    return {"message": "Location deleted successfully"}
