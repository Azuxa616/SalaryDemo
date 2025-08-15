from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.base import Base, engine
from app.api.routes.auth import router as auth_router
from app.api.routes.projects import router as projects_router
from app.api.routes.worklogs import router as worklogs_router
from app.api.routes.salary_config import router as salary_config_router
from app.core.config import BASE_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    try:
        # 创建数据库表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
    
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
    
    yield
    
    # 关闭时执行（如果需要的话）
    pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(worklogs_router)
app.include_router(salary_config_router)


# 如果直接运行此文件，则启动服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )