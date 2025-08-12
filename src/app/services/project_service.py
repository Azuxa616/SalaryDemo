from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.project import Project, ProjectCreate, ProjectUpdate
from app.models.user import User


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_project(self, project_data: ProjectCreate, current_user: User) -> Project:
        """创建新项目"""
        # 检查项目名称是否已存在
        existing_project = self.db.query(Project).filter(
            func.lower(Project.name) == func.lower(project_data.name)
        ).first()
        
        if existing_project:
            raise ValueError("项目名称已存在")
        
        project = Project(**project_data.model_dump())
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: UUID) -> Optional[Project]:
        """根据ID获取项目"""
        return self.db.query(Project).filter(Project.id == project_id).first()

    def get_projects(
        self, 
        skip: int = 0, 
        limit: int = 100,
        name: Optional[str] = None
    ) -> tuple[list[Project], int]:
        """获取项目列表，支持分页和名称搜索"""
        query = self.db.query(Project)
        
        if name:
            query = query.filter(Project.name.ilike(f"%{name}%"))
        
        total = query.count()
        projects = query.offset(skip).limit(limit).all()
        
        return projects, total

    def update_project(
        self, 
        project_id: UUID, 
        project_data: ProjectUpdate,
        current_user: User
    ) -> Optional[Project]:
        """更新项目信息"""
        project = self.get_project(project_id)
        if not project:
            return None
        
        # 如果要更新名称，检查是否与其他项目重复
        if project_data.name and project_data.name != project.name:
            existing_project = self.db.query(Project).filter(
                Project.id != project_id,
                func.lower(Project.name) == func.lower(project_data.name)
            ).first()
            
            if existing_project:
                raise ValueError("项目名称已存在")
        
        # 更新字段
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: UUID, current_user: User) -> bool:
        """删除项目"""
        project = self.get_project(project_id)
        if not project:
            return False
        
        # 检查是否有工作记录关联到此项目
        from app.models.worklog import WorkLog
        worklog_count = self.db.query(WorkLog).filter(WorkLog.project_id == project_id).count()
        
        if worklog_count > 0:
            raise ValueError("无法删除项目：存在关联的工作记录")
        
        self.db.delete(project)
        self.db.commit()
        return True

    def check_project_exists(self, project_id: UUID) -> bool:
        """检查项目是否存在"""
        return self.db.query(Project).filter(Project.id == project_id).first() is not None
