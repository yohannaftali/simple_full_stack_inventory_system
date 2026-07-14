"""Material master-data CRUD admin screen (frontend module `master_material`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_material")`.
Each material optionally links to a supplier (`supplier_id`, nullable —
existing materials predate the supplier link); the edit/new form's
`supplier_id` field is a `select` sourced from `call_supplier_id_select`.
"""

from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.exc import IntegrityError

from core.table_export import export_response
from core.table_query import attach_pagination
from models.material import MaterialModel
from models.user import UserModel
from repository.material_repository import MaterialRepository
from repository.supplier_repository import SupplierRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_master_material", tags=["master-material"])
_material_repository = MaterialRepository()
_supplier_repository = SupplierRepository()

_require_access = require_module_access("master_material")

_EXPORT_COLUMNS = [
    ("material_code", "Material Code"),
    ("material_name", "Material Name"),
    ("supplier_name", "Supplier"),
]


def _serialize(material: MaterialModel) -> dict:
    supplier = (
        _supplier_repository.get_supplier_by_id(material.supplier_id)
        if material.supplier_id
        else None
    )
    return {
        "id": material.id,
        "material_code": material.material_code,
        "material_name": material.material_name,
        "supplier_id": str(material.supplier_id) if material.supplier_id else "",
        "supplier_name": supplier.name if supplier else "",
    }


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    rows, pagination = _material_repository.list_materials(
        keyword=keyword, limit=limit, page=page, offset=offset
    )
    return attach_pagination([_serialize(material) for material in rows], pagination)


@router.get("/export_detail")
def export_detail(
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    rows, _pagination = _material_repository.list_materials(keyword=keyword, limit=0, page=1, offset=0)
    return export_response(
        [_serialize(material) for material in rows], _EXPORT_COLUMNS, format, "master_material"
    )


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
    supplier_id: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    supplier_id_value = int(supplier_id) if supplier_id else None

    if id:
        updated = _material_repository.update_material(
            int(id),
            material_code=material_code,
            material_name=material_name,
            supplier_id=supplier_id_value,
        )
        if not updated:
            return {"error": "Material not found"}
        return {"message": "Material updated successfully"}

    _material_repository.create_material(
        material_code=material_code,
        material_name=material_name,
        supplier_id=supplier_id_value,
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


@router.get("/call_supplier_id_select")
def call_supplier_id_select(user: UserModel = Depends(_require_access)) -> list:
    return [
        {"value": str(s.id), "label": f"{s.code} - {s.name}"}
        for s in _supplier_repository.get_all_suppliers()
    ]
