"""
Celery 定时任务配置
"""
import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

# Redis 连接配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery 应用配置
celery_app = Celery(
    "salary_calculation",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.app.tasks.salary_tasks"]
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化格式
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区设置
    timezone="UTC",
    enable_utc=True,
    
    # 任务结果过期时间
    result_expires=3600,  # 1小时
    
    # 工作进程配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # 任务路由
    task_routes={
        "src.app.tasks.salary_tasks.*": {"queue": "salary_calculation"}
    },
    
    # 定时任务配置 - 只保留一个核心任务
    beat_schedule={
        # 每分钟检查一次待执行的定时批次
        "check-scheduled-batches-minute": {
            "task": "src.app.tasks.salary_tasks.check_scheduled_batches",
            "schedule": crontab(minute="*"),  # 每分钟执行
        },
    }
)

# 任务执行配置
celery_app.conf.task_annotations = {
    "src.app.tasks.salary_tasks.*": {
        "rate_limit": "1/m",  # 每分钟最多1个任务
        "time_limit": 300,     # 任务超时5分钟
        "soft_time_limit": 240,  # 软超时4分钟
    }
}

if __name__ == "__main__":
    celery_app.start()
