from fastapi import FastAPI
from app.db.base import Base, engine
from app.api.routes.auth import router as auth_router
from app.api.routes.projects import router as projects_router
from app.api.routes.worklogs import router as worklogs_router
from app.core.config import BASE_URL
from fastapi import FastAPI
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(worklogs_router)


@app.on_event("startup")
async def print_startup_banner() -> None:
    base = BASE_URL.rstrip("/")
    docs = f"{base}/docs"
    redoc = f"{base}/redoc"
    banner_lines = [
        "\n" + "=" * 70,
        " FastAPI 服务已启动",
        f" Base URL : {base}",
        f" Swagger  : {docs}",
        f" ReDoc    : {redoc}",
        "=" * 70 + "\n",
    ]
    for line in banner_lines:
        print(line)