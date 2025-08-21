from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.app.api.deps import get_db, get_current_user, require_role
from src.app.models.user import User
from src.app.models.project import ProjectCreate, ProjectUpdate, ProjectOut, ProjectList
from src.app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=ProjectList)
def get_projects(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    name: Optional[str] = Query(None, description="项目名称搜索"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取项目列表
    - 所有用户（1-4级）都可以查看
    - 支持分页和名称搜索
    """
    project_service = ProjectService(db)
    projects, total = project_service.get_projects(skip=skip, limit=limit, name=name)
    
    return ProjectList(
        projects=[ProjectOut.model_validate(project) for project in projects],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        size=limit
    )





@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(require_role(3)),  # 3级及以上可创建
    db: Session = Depends(get_db)
):
    """
    创建新项目
    - 需要3级及以上权限（管理员、超级管理员）
    """
    project_service = ProjectService(db)
    
    try:
        project = project_service.create_project(project_data, current_user)
        return ProjectOut.model_validate(project)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(require_role(3)),  # 3级及以上可更新
    db: Session = Depends(get_db)
):
    """
    更新项目信息
    - 需要3级及以上权限（管理员、超级管理员）
    """
    project_service = ProjectService(db)
    
    try:
        project = project_service.update_project(project_id, project_data, current_user)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )
        return ProjectOut.model_validate(project)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{project_id}", response_model=ProjectOut)
def partial_update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(require_role(3)),  # 3级及以上可更新
    db: Session = Depends(get_db)
):
    """
    部分更新项目信息
    - 需要3级及以上权限（管理员、超级管理员）
    """
    project_service = ProjectService(db)
    
    try:
        project = project_service.update_project(project_id, project_data, current_user)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )
        return ProjectOut.model_validate(project)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    current_user: User = Depends(require_role(3)),  # 3级及以上可删除
    db: Session = Depends(get_db)
):
    """
    删除项目
    - 需要3级及以上权限（管理员、超级管理员）
    - 如果项目有关联的工作记录，则无法删除
    """
    project_service = ProjectService(db)
    
    try:
        success = project_service.delete_project(project_id, current_user)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
