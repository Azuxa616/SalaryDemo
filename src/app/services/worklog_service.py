from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.app.models.worklog import WorkLog, WorkLogCreate, WorkLogUpdate
from src.app.models.user import User


class WorkLogService:
    def __init__(self, db: Session):
        self.db = db

    def _is_low_level_user(self, current_user: User) -> bool:
        """检查是否为低级别用户（1-2级）"""
        try:
            # 重新查询用户以确保获取到正确的role值
            user = self.db.query(User).filter(User.id == current_user.id).first()
            if user and hasattr(user, 'role') and user.role is not None:
                # 使用字符串比较避免类型转换问题
                role_str = str(user.role)
                return role_str in ['1', '2']
            return True  # 默认视为低级别用户
        except Exception:
            return True  # 任何异常都默认视为低级别用户

    def create_worklog(self, worklog_data: WorkLogCreate, current_user: User) -> WorkLog:
        """创建工作记录"""
        # 检查员工ID是否存在
        from src.app.models.user import User
        employee = self.db.query(User).filter(User.id == worklog_data.employee_id).first()
        if not employee:
            raise ValueError("员工不存在")
        
        # 检查项目ID是否存在
        from src.app.models.project import Project
        project = self.db.query(Project).filter(Project.id == worklog_data.project_id).first()
        if not project:
            raise ValueError("项目不存在")
        
        # 创建新工作记录，状态默认为0（待核算）
        worklog = WorkLog(
            **worklog_data.model_dump(),
            status=0  # 默认状态为待核算
        )
        
        self.db.add(worklog)
        self.db.commit()
        self.db.refresh(worklog)
        return worklog

    def get_worklog(self, worklog_id: UUID, current_user: User) -> Optional[WorkLog]:
        """根据ID获取工作记录"""
        worklog = self.db.query(WorkLog).filter(WorkLog.entry_id == worklog_id).first()
        
        if not worklog:
            return None
        
        # 权限检查：2级及以下用户只能查看自己的记录
        if self._is_low_level_user(current_user) and str(worklog.employee_id) != str(current_user.id):
            raise ValueError("权限不足：只能查看自己的工作记录")
        
        return worklog

    def get_worklogs(
        self, 
        skip: int = 0, 
        limit: int = 100,
        employee_id: Optional[int] = None,
        project_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[int] = None,
        current_user: Optional[User] = None
    ) -> Tuple[List[WorkLog], int]:
        """获取工作记录列表，支持分页和多种筛选条件"""
        query = self.db.query(WorkLog)
        
        # 权限过滤：2级及以下用户只能查看自己的记录
        if current_user and self._is_low_level_user(current_user):
            query = query.filter(WorkLog.employee_id == current_user.id)
        
        # 应用筛选条件
        if employee_id is not None:
            query = query.filter(WorkLog.employee_id == employee_id)
        if project_id is not None:
            query = query.filter(WorkLog.project_id == project_id)
        if date_from is not None:
            query = query.filter(WorkLog.date >= date_from)
        if date_to is not None:
            query = query.filter(WorkLog.date <= date_to)
        if status is not None:
            query = query.filter(WorkLog.status == status)
        
        total = query.count()
        worklogs = query.order_by(WorkLog.date.desc(), WorkLog.created_at.desc()).offset(skip).limit(limit).all()
        
        return worklogs, total

    def update_worklog(
        self, 
        worklog_id: UUID, 
        worklog_data: WorkLogUpdate,
        current_user: User
    ) -> Optional[WorkLog]:
        """更新工作记录"""
        worklog = self.get_worklog(worklog_id, current_user)
        if not worklog:
            return None
        
        # 权限检查：2级及以下用户只能修改状态为"未核算"(0)的记录
        if self._is_low_level_user(current_user) and str(worklog.status) != '0':
            raise ValueError("权限不足：只能修改未核算的工作记录")
        
        # 更新字段
        update_data = worklog_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(worklog, field, value)
        
        self.db.commit()
        self.db.refresh(worklog)
        return worklog

    def delete_worklog(self, worklog_id: UUID, current_user: User) -> bool:
        """删除工作记录"""
        worklog = self.get_worklog(worklog_id, current_user)
        if not worklog:
            return False
        
        # 权限检查：2级及以下用户只能删除状态为"未核算"(0)的记录
        if self._is_low_level_user(current_user) and str(worklog.status) != '0':
            raise ValueError("权限不足：只能删除未核算的工作记录")
        
        self.db.delete(worklog)
        self.db.commit()
        return True

    def update_status(self, worklog_id: UUID, new_status: int, current_user: User) -> Optional[WorkLog]:
        """更新工作记录状态（仅限3-4级用户）"""
        if self._is_low_level_user(current_user):
            raise ValueError("权限不足：只有管理员及以上权限可以修改状态")
        
        if new_status not in [0, 1, 2]:
            raise ValueError("状态值无效：必须是0、1或2")
        
        worklog = self.db.query(WorkLog).filter(WorkLog.entry_id == worklog_id).first()
        if not worklog:
            return None
        
        setattr(worklog, 'status', new_status)
        self.db.commit()
        self.db.refresh(worklog)
        return worklog

    def get_worklog_summary(
        self, 
        employee_id: Optional[int] = None,
        project_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        current_user: Optional[User] = None
    ) -> dict:
        """获取工作记录统计摘要"""
        query = self.db.query(WorkLog)
        
        # 权限过滤：2级及以下用户只能查看自己的记录
        if current_user and self._is_low_level_user(current_user):
            query = query.filter(WorkLog.employee_id == current_user.id)
        
        # 应用筛选条件
        if employee_id is not None:
            query = query.filter(WorkLog.employee_id == employee_id)
        if project_id is not None:
            query = query.filter(WorkLog.project_id == project_id)
        if date_from is not None:
            query = query.filter(WorkLog.date >= date_from)
        if date_to is not None:
            query = query.filter(WorkLog.date <= date_to)
        
        # 计算统计信息
        total_hours = query.with_entities(func.sum(WorkLog.hours)).scalar() or 0
        total_records = query.count()
        
        # 按状态统计 - 修复filter方法调用
        base_query = self.db.query(WorkLog)
        if current_user and self._is_low_level_user(current_user):
            base_query = base_query.filter(WorkLog.employee_id == current_user.id)
        
        # 应用筛选条件到基础查询
        if employee_id is not None:
            base_query = base_query.filter(WorkLog.employee_id == employee_id)
        if project_id is not None:
            base_query = base_query.filter(WorkLog.project_id == project_id)
        if date_from is not None:
            base_query = base_query.filter(WorkLog.date >= date_from)
        if date_to is not None:
            base_query = base_query.filter(WorkLog.date <= date_to)
        
        status_stats = base_query.with_entities(
            WorkLog.status,
            func.count(WorkLog.entry_id).label('count'),
            func.sum(WorkLog.hours).label('total_hours')
        ).group_by(WorkLog.status).all()
        
        return {
            "total_records": total_records,
            "total_hours": float(total_hours),
            "status_breakdown": [
                {
                    "status": stat.status,
                    "count": stat.count,
                    "total_hours": float(stat.total_hours or 0)
                }
                for stat in status_stats
            ]
        }

    def check_worklog_exists(self, worklog_id: UUID) -> bool:
        """检查工作记录是否存在"""
        return self.db.query(WorkLog).filter(WorkLog.entry_id == worklog_id).first() is not None
