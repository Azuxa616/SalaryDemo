import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.app.db.base import Base, engine
from src.app.api.routes.auth import router as auth_router
from src.app.api.routes.projects import router as projects_router
from src.app.api.routes.worklogs import router as worklogs_router
from src.app.api.routes.salary_config import router as salary_config_router
from src.app.api.routes.salary_calculation import router as salary_calculation_router
from src.app.api.routes.task_management import router as task_management_router
from src.app.core.config import BASE_URL
from src.app.core.scheduler import scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    try:
        # 创建数据库表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
    
    # 启动定时任务调度器
    try:
        await scheduler.start()
        print("✅ 定时任务调度器启动成功")
    except Exception as e:
        print(f"❌ 定时任务调度器启动失败: {e}")
    
    base = BASE_URL.rstrip("/")
    docs = f"{base}/docs"
    redoc = f"{base}/redoc"
    banner_lines = [
        "\n" + "=" * 70,
        " FastAPI 服务已启动",
        f" Base URL : {base}",
        f" Swagger  : {docs}",
        f" ReDoc    : {redoc}",
        " 定时任务调度器已启动",
        "=" * 70 + "\n",
    ]
    for line in banner_lines:
        print(line)
    
    yield
    
    # 关闭时执行
    try:
        await scheduler.stop()
        print("✅ 定时任务调度器已停止")
    except Exception as e:
        print(f"❌ 定时任务调度器停止失败: {e}")


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


@app.get("/scheduler/status")
async def get_scheduler_status():
    """获取定时任务调度器状态"""
    return scheduler.get_status()


app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(worklogs_router)
app.include_router(salary_config_router)
app.include_router(salary_calculation_router)
app.include_router(task_management_router)


# 如果直接运行此文件，则启动服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="debug"
    )