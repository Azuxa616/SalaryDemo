from typing import Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.worklog import WorkLogCreate, WorkLogUpdate, WorkLogOut, WorkLogList
from app.services.worklog_service import WorkLogService

router = APIRouter(prefix="/worklogs", tags=["worklogs"])


@router.get("/", response_model=WorkLogList)
def get_worklogs(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    employee_id: Optional[str] = Query(None, description="员工ID筛选"),
    project_id: Optional[str] = Query(None, description="项目ID筛选"),
    date_from: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="状态筛选：0=待核算，1=已核算，2=保留"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取工作记录列表
    - 所有用户（1-4级）都可以查看
    - 2级及以下用户只能查看自己的记录
    - 3-4级用户可以查看所有记录
    - 支持多种筛选条件和分页
    """
    # 参数验证和转换
    parsed_employee_id = None
    if employee_id and employee_id.strip():
        try:
            parsed_employee_id = int(employee_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="员工ID必须是有效的整数"
            )
    
    parsed_project_id = None
    if project_id and project_id.strip():
        try:
            parsed_project_id = UUID(project_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="项目ID必须是有效的UUID"
            )
    
    parsed_date_from = None
    if date_from and date_from.strip():
        try:
            parsed_date_from = date.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="开始日期格式无效，请使用YYYY-MM-DD格式"
            )
    
    parsed_date_to = None
    if date_to and date_to.strip():
        try:
            parsed_date_to = date.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="结束日期格式无效，请使用YYYY-MM-DD格式"
            )
    
    parsed_status = None
    if status and status.strip():
        try:
            parsed_status = int(status)
            if parsed_status not in [0, 1, 2]:
                raise ValueError("状态值无效")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="状态值无效：必须是0、1或2"
            )
    
    worklog_service = WorkLogService(db)
    worklogs, total = worklog_service.get_worklogs(
        skip=skip, 
        limit=limit, 
        employee_id=parsed_employee_id,
        project_id=parsed_project_id,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        status=parsed_status,
        current_user=current_user
    )
    
    return WorkLogList(
        worklogs=[WorkLogOut.model_validate(worklog) for worklog in worklogs],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        size=limit
    )


@router.get("/{worklog_id}", response_model=WorkLogOut)
def get_worklog(
    worklog_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    根据ID获取工作记录详情
    - 所有用户（1-4级）都可以查看
    - 2级及以下用户只能查看自己的记录
    """
    worklog_service = WorkLogService(db)
    
    try:
        worklog = worklog_service.get_worklog(worklog_id, current_user)
        if not worklog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作记录不存在"
            )
        return WorkLogOut.model_validate(worklog)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/", response_model=WorkLogOut, status_code=status.HTTP_201_CREATED)
def create_worklog(
    worklog_data: WorkLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建新工作记录
    - 所有用户（1-4级）都可以创建
    - 2级及以下用户只能为自己创建记录
    - 新记录状态默认为"待核算"(0)
    """
    worklog_service = WorkLogService(db)
    
    # 权限检查：2级及以下用户只能为自己创建记录
    if str(current_user.role) in ['1', '2'] and worklog_data.employee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：只能为自己创建工作记录"
        )
    
    try:
        worklog = worklog_service.create_worklog(worklog_data, current_user)
        return WorkLogOut.model_validate(worklog)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{worklog_id}", response_model=WorkLogOut)
def update_worklog(
    worklog_id: UUID,
    worklog_data: WorkLogUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新工作记录信息
    - 所有用户（1-4级）都可以更新
    - 2级及以下用户只能修改状态为"未核算"(0)的记录
    - 3-4级用户可以修改任何状态的记录
    """
    worklog_service = WorkLogService(db)
    
    try:
        worklog = worklog_service.update_worklog(worklog_id, worklog_data, current_user)
        if not worklog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作记录不存在"
            )
        return WorkLogOut.model_validate(worklog)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{worklog_id}", response_model=WorkLogOut)
def partial_update_worklog(
    worklog_id: UUID,
    worklog_data: WorkLogUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    部分更新工作记录信息
    - 所有用户（1-4级）都可以更新
    - 2级及以下用户只能修改状态为"未核算"(0)的记录
    - 3-4级用户可以修改任何状态的记录
    """
    worklog_service = WorkLogService(db)
    
    try:
        worklog = worklog_service.update_worklog(worklog_id, worklog_data, current_user)
        if not worklog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作记录不存在"
            )
        return WorkLogOut.model_validate(worklog)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{worklog_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worklog(
    worklog_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除工作记录
    - 所有用户（1-4级）都可以删除
    - 2级及以下用户只能删除状态为"未核算"(0)的记录
    - 3-4级用户可以删除任何状态的记录
    """
    worklog_service = WorkLogService(db)
    
    try:
        success = worklog_service.delete_worklog(worklog_id, current_user)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作记录不存在"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{worklog_id}/status")
def update_worklog_status(
    worklog_id: UUID,
    new_status: int = Query(..., ge=0, le=2, description="新状态：0=待核算，1=已核算，2=保留"),
    current_user: User = Depends(require_role(3)),  # 只有3级及以上可修改状态
    db: Session = Depends(get_db)
):
    """
    更新工作记录状态
    - 需要3级及以上权限（管理员、超级管理员）
    - 状态值：0=待核算，1=已核算，2=保留
    """
    worklog_service = WorkLogService(db)
    
    try:
        worklog = worklog_service.update_status(worklog_id, new_status, current_user)
        if not worklog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作记录不存在"
            )
        return {"message": "状态更新成功", "worklog_id": str(worklog_id), "new_status": new_status}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/summary/statistics")
def get_worklog_statistics(
    employee_id: Optional[str] = Query(None, description="员工ID筛选"),
    project_id: Optional[str] = Query(None, description="项目ID筛选"),
    date_from: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取工作记录统计摘要
    - 所有用户（1-4级）都可以查看
    - 2级及以下用户只能查看自己的统计
    - 3-4级用户可以查看所有统计
    """
    # 参数验证和转换
    parsed_employee_id = None
    if employee_id and employee_id.strip():
        try:
            parsed_employee_id = int(employee_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="员工ID必须是有效的整数"
            )
    
    parsed_project_id = None
    if project_id and project_id.strip():
        try:
            parsed_project_id = UUID(project_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="项目ID必须是有效的UUID"
            )
    
    parsed_date_from = None
    if date_from and date_from.strip():
        try:
            parsed_date_from = date.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="开始日期格式无效，请使用YYYY-MM-DD格式"
            )
    
    parsed_date_to = None
    if date_to and date_to.strip():
        try:
            parsed_date_to = date.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="结束日期格式无效，请使用YYYY-MM-DD格式"
            )
    
    worklog_service = WorkLogService(db)
    
    try:
        summary = worklog_service.get_worklog_summary(
            employee_id=parsed_employee_id,
            project_id=parsed_project_id,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            current_user=current_user
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )
