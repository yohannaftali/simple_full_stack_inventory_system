"""Material master-data CRUD admin screen (frontend module `master_material`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_material")`.
"""

import math

from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.exc import IntegrityError

from models.material import MaterialModel
from models.user import UserModel
from repository.material_repository import MaterialRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_master_material", tags=["master-material"])
_material_repository = MaterialRepository()

_require_access = require_module_access("master_material")


def _serialize(material: MaterialModel) -> dict:
    return {
        "id": material.id,
        "material_code": material.material_code,
        "material_name": material.material_name,
    }


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    effective_offset = offset if offset else max(page - 1, 0) * limit
    rows, total = _material_repository.list_materials(
        keyword=keyword, limit=limit, offset=effective_offset
    )
    total_pages = max(math.ceil(total / limit), 1) if limit else 1

    result = []
    for material in rows:
        row = _serialize(material)
        row["db_total_page"] = total_pages
        row["db_num_rows"] = total
        result.append(row)
    return result


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    material = _material_repository.get_material_by_id(id)
    if material is None:
        return {"error": "Material not found"}
    return _serialize(material)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    material_code: str = Form(...),
    material_name: str = Form(...),
    user: UserModel = Depends(_require_access),
) -> dict:
    if id:
        updated = _material_repository.update_material(
            int(id), material_code=material_code, material_name=material_name
        )
        if not updated:
            return {"error": "Material not found"}
        return {"message": "Material updated successfully"}

    _material_repository.create_material(
        material_code=material_code, material_name=material_name
    )
    return {"message": "Material created successfully"}


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    try:
        deleted = _material_repository.delete_material(int(id))
    except IntegrityError:
        return {"error": "Cannot delete: this material has receiving/stock/issue history"}
    if not deleted:
        return {"error": "Material not found"}
    return {"message": "Material deleted successfully"}
