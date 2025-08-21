from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.app.core.config import DATABASE_URL

# PostgreSQL 使用 psycopg 驱动；不需要 sqlite 的 check_same_thread
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 引入模型，确保 Base.metadata 能收集到表
# 如果新增模型，请在此处导入
try:
    from src.app.models.user import User  # noqa: F401
    from src.app.models.project import Project  # noqa: F401
    from src.app.models.worklog import WorkLog  # noqa: F401
    from src.app.models.salary_engine import (  # noqa: F401
        SalaryRule,
        SalaryCalculationBatch,
        SalaryCalculationResult,
        EmployeeSalaryConfig,
        DeductionConfig
    )
except Exception as e:
    print(f"Warning: Failed to import models: {e}")
    pass