"""
定时任务管理API路由
- 手动触发定时任务
- 查询任务状态
- 查询活跃任务
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.app.api.deps import get_db, require_role
from src.app.core.roles import ROLE_ADMIN

router = APIRouter(prefix="/task-management", tags=["task-management"])


@router.post("/check-scheduled")
async def check_scheduled_batches_task(
    db: Session = Depends(get_db),
    current_user = Depends(require_role(ROLE_ADMIN))
):
    """手动触发检查定时批次任务"""
    try:
        from src.app.tasks.salary_tasks import check_scheduled_batches
        task = check_scheduled_batches.delay()
        return {
            "success": True,
            "message": "检查定时批次任务已触发",
            "task_id": task.id,
            "status": "PENDING"
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="定时任务系统未配置")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发任务失败: {str(e)}")


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user = Depends(require_role(ROLE_ADMIN))
):
    """查询任务执行状态"""
    try:
        from src.app.core.celery_config import celery_app
        result = celery_app.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready()
        }
        
        if result.ready():
            if result.successful():
                response["result"] = result.result
            else:
                response["error"] = str(result.info)
        
        return response
    except ImportError:
        raise HTTPException(status_code=500, detail="定时任务系统未配置")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@router.get("/active")
async def get_active_tasks(
    current_user = Depends(require_role(ROLE_ADMIN))
):
    """查询活跃任务列表"""
    try:
        from src.app.core.celery_config import celery_app
        inspector = celery_app.control.inspect()
        
        active_tasks = inspector.active()
        reserved_tasks = inspector.reserved()
        
        result = {
            "active_tasks": active_tasks or {},
            "reserved_tasks": reserved_tasks or {},
            "total_active": sum(len(tasks) for tasks in (active_tasks or {}).values()),
            "total_reserved": sum(len(tasks) for tasks in (reserved_tasks or {}).values())
        }
        
        return result
    except ImportError:
        raise HTTPException(status_code=500, detail="定时任务系统未配置")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询活跃任务失败: {str(e)}")
