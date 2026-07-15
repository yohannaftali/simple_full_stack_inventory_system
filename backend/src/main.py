from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from core.config import JWT_SECRET
from routers.app_config import router as app_config_router
from routers.home import router as home_router
from routers.login import router as login_router
from routers.mail_config import router as mail_config_router
from routers.master_category import router as master_category_router
from routers.master_department import router as master_department_router
from routers.master_location import router as master_location_router
from routers.master_material import router as master_material_router
from routers.master_supplier import router as master_supplier_router
from routers.module import router as module_router
from routers.module_admin import router as module_admin_router
from routers.module_group_admin import router as module_group_admin_router
from routers.stock_browse import router as stock_browse_router
from routers.stock_in import router as stock_in_router
from routers.stock_out import router as stock_out_router
from routers.usage_report import router as usage_report_router
from routers.user_admin import router as user_admin_router

app = FastAPI(title="SFSIS API")
app.add_middleware(
    SessionMiddleware,
    secret_key=JWT_SECRET,
    same_site="lax",
    https_only=False,
)
app.include_router(login_router)
app.include_router(home_router)
app.include_router(module_admin_router)
app.include_router(module_group_admin_router)
app.include_router(user_admin_router)
app.include_router(master_location_router)
app.include_router(master_material_router)
app.include_router(master_supplier_router)
app.include_router(master_department_router)
app.include_router(master_category_router)
app.include_router(stock_in_router)
app.include_router(stock_out_router)
app.include_router(stock_browse_router)
app.include_router(usage_report_router)
app.include_router(app_config_router)
app.include_router(mail_config_router)
app.include_router(module_router)


@app.get("/")
def read_root():
    return {"status": "ok"}
