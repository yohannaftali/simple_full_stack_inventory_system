from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from core.config import JWT_SECRET
from routers.home import router as home_router
from routers.login import router as login_router
from routers.module import router as module_router
from routers.module_admin import router as module_admin_router
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
app.include_router(user_admin_router)
app.include_router(module_router)


@app.get("/")
def read_root():
    return {"status": "ok"}
