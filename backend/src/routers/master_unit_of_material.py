"""Unit of material master-data admin screen (frontend module
`master_unit_of_material`).

Same list/get/submit contract as `master_location.py` — see that file's
docstring for the shape — with one deliberate difference: **no delete
endpoint**. A unit of material can never be removed once created; every
material links to exactly one (`materials.unit_id`, non-nullable), so
deleting a unit out from under an in-use material would break that link the
same way deleting a material with transaction history would break referential
integrity. Gated by `require_module_access("master_unit_of_material")`.
"""

from fastapi import APIRouter, Depends, Form, Query, Request

from core.table_export import export_response
from core.table_query import attach_pagination, parse_sort_fields
from models.unit_of_material import UnitOfMaterialModel
from models.user import UserModel
from repository.unit_of_material_repository import UnitOfMaterialRepository
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_master_unit_of_material", tags=["master-unit-of-material"])
_unit_repository = UnitOfMaterialRepository()

_require_access = require_module_access("master_unit_of_material")

_EXPORT_COLUMNS = [("code", "Code"), ("name", "Name")]


def _serialize(unit: UnitOfMaterialModel) -> dict:
    return {"id": unit.id, "code": unit.code, "name": unit.name}


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
    rows, pagination = _unit_repository.list_units(
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination([_serialize(unit) for unit in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _unit_repository.list_units(
        keyword=keyword,
        query_params=request.query_params,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        [_serialize(unit) for unit in rows], _EXPORT_COLUMNS, format, "master_unit_of_material"
    )


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    unit = _unit_repository.get_unit_by_id(id)
    if unit is None:
        return {"error": "Unit of material not found"}
    return _serialize(unit)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    code: str = Form(...),
    name: str = Form(...),
    user: UserModel = Depends(_require_access),
) -> dict:
    if id:
        updated = _unit_repository.update_unit(int(id), code=code, name=name)
        if not updated:
            return {"error": "Unit of material not found"}
        return {"message": "Unit of material updated successfully"}

    _unit_repository.create_unit(code=code, name=name)
    return {"message": "Unit of material created successfully"}


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(form, ["code", "name"])

    def build(row, session):
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        if not code or not name:
            raise BulkRowError(row["_row"], "Code and Name are required")
        return UnitOfMaterialModel(code=code, name=name)

    return bulk_create(rows, build)
