"""Material master-data CRUD admin screen (frontend module `master_material`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_material")`.
Each material optionally links to a supplier (`supplier_id`, nullable —
existing materials predate the supplier link); the edit/new form's
`supplier_id` field is a `select` sourced from `call_supplier_id_select`.
"""

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.exc import IntegrityError

from core.table_export import export_response
from core.table_query import attach_pagination
from models.material import MaterialModel
from models.user import UserModel
from repository.category_repository import CategoryRepository
from repository.material_repository import MaterialRepository
from repository.supplier_repository import SupplierRepository
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_master_material", tags=["master-material"])
_material_repository = MaterialRepository()
_supplier_repository = SupplierRepository()
_category_repository = CategoryRepository()

_require_access = require_module_access("master_material")

_EXPORT_COLUMNS = [
    ("material_code", "Material Code"),
    ("material_name", "Material Name"),
    ("supplier_name", "Supplier"),
    ("category_name", "Category"),
]


def _serialize(material: MaterialModel) -> dict:
    supplier = (
        _supplier_repository.get_supplier_by_id(material.supplier_id)
        if material.supplier_id
        else None
    )
    category = (
        _category_repository.get_category_by_id(material.category_id)
        if material.category_id
        else None
    )
    return {
        "id": material.id,
        "material_code": material.material_code,
        "material_name": material.material_name,
        "supplier_id": str(material.supplier_id) if material.supplier_id else "",
        "supplier_name": supplier.name if supplier else "",
        "category_id": str(material.category_id) if material.category_id else "",
        "category_name": category.name if category else "",
    }


@router.get("/get_detail")
def get_detail(
    request: Request,
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    rows, pagination = _material_repository.list_materials(
        keyword=keyword, query_params=request.query_params, limit=limit, page=page, offset=offset
    )
    return attach_pagination([_serialize(material) for material in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    rows, _pagination = _material_repository.list_materials(
        keyword=keyword, query_params=request.query_params, limit=0, page=1, offset=0
    )
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
    category_id: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    supplier_id_value = int(supplier_id) if supplier_id else None
    category_id_value = int(category_id) if category_id else None

    if id:
        updated = _material_repository.update_material(
            int(id),
            material_code=material_code,
            material_name=material_name,
            supplier_id=supplier_id_value,
            category_id=category_id_value,
        )
        if not updated:
            return {"error": "Material not found"}
        return {"message": "Material updated successfully"}

    _material_repository.create_material(
        material_code=material_code,
        material_name=material_name,
        supplier_id=supplier_id_value,
        category_id=category_id_value,
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


@router.get("/call_category_id_select")
def call_category_id_select(user: UserModel = Depends(_require_access)) -> list:
    return [
        {"value": str(c.id), "label": f"{c.code} - {c.name}"}
        for c in _category_repository.get_all_categories()
    ]


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(
        form, ["material_code", "material_name", "supplier_id", "category_id"]
    )

    def build(row, session):
        material_code = str(row.get("material_code", "")).strip()
        material_name = str(row.get("material_name", "")).strip()
        if not material_code or not material_name:
            raise BulkRowError(row["_row"], "Code and Name are required")
        supplier_id_raw = str(row.get("supplier_id", "")).strip()
        try:
            supplier_id = int(supplier_id_raw) if supplier_id_raw else None
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid Supplier: {supplier_id_raw}")
        category_id_raw = str(row.get("category_id", "")).strip()
        try:
            category_id = int(category_id_raw) if category_id_raw else None
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid Category: {category_id_raw}")
        return MaterialModel(
            material_code=material_code,
            material_name=material_name,
            supplier_id=supplier_id,
            category_id=category_id,
        )

    return bulk_create(rows, build)
