"""
员工薪资配置API路由
实现增删改查功能，包含权限控制
"""

from typing import List, Optional, cast
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import date, datetime
from pydantic import BaseModel, Field
import logging
from uuid import UUID

from src.app.api.deps import get_db, get_current_user, require_role
from src.app.core.roles import ROLE_ADMIN, ROLE_SUPERADMIN
from src.app.models.user import User
from src.app.models.salary_engine import (
    EmployeeSalaryConfig, 
    EmployeeSalaryConfigCreate, 
    EmployeeSalaryConfigUpdate, 
    EmployeeSalaryConfigOut,
    EmployeeSalaryConfigList,
    SalaryCalculationBatch
)
from src.app.services.salary_calculation_service import SalaryCalculationService

router = APIRouter(prefix="/salary-config", tags=["salary-config"])

"""
注意：计算相关接口已迁移至 `salary_calculation.py`。
此文件仅保留薪资配置CRUD相关接口。
"""


def can_access_employee(current_user: User, target_employee_id: int, db: Session) -> bool:
    """
    检查当前用户是否有权限访问目标员工
    规则：只能访问权限等级小于自身的员工
    """
    current_role = cast(int, current_user.role)
    if current_role >= ROLE_SUPERADMIN:
        return True
    
    target_user = db.query(User).filter(User.id == target_employee_id).first()
    if not target_user:
        return False
    
    target_role = cast(int, target_user.role)
    return bool(current_role > target_role)


@router.post("/", response_model=EmployeeSalaryConfigOut)
def create_salary_config(
    config_in: EmployeeSalaryConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_SUPERADMIN))
):
    """
    创建员工薪资配置
    仅超级管理员(权限等级4)可使用
    """
    # 检查员工是否存在
    employee = db.query(User).filter(User.id == config_in.employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # 检查是否已存在该员工的薪资配置
    existing_config = db.query(EmployeeSalaryConfig).filter(
        EmployeeSalaryConfig.employee_id == config_in.employee_id,
        EmployeeSalaryConfig.effective_from == config_in.effective_from,
        EmployeeSalaryConfig.is_active.is_(True)
    ).first()
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salary config already exists for this employee and effective date"
        )
    
    # 创建新的薪资配置
    salary_config = EmployeeSalaryConfig(**config_in.dict())
    db.add(salary_config)
    db.commit()
    db.refresh(salary_config)
    
    return EmployeeSalaryConfigOut.from_orm(salary_config)


@router.get("/", response_model=EmployeeSalaryConfigList)
def list_salary_configs(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    employee_id: Optional[str] = Query(None, description="员工ID筛选"),
    department_id: Optional[str] = Query(None, description="部门ID筛选"),
    is_active: Optional[str] = Query(None, description="是否激活"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_ADMIN))
):
    """
    查询所有员工薪资配置
    仅管理员及以上权限(等级3+)可使用
    只能查看权限等级小于自身的员工
    """
    # 构建查询条件
    query = db.query(EmployeeSalaryConfig)
    
    # 权限过滤：只能查看权限等级小于自身的员工
    current_role = cast(int, current_user.role)
    if current_role < ROLE_SUPERADMIN:
        # 获取所有权限等级小于当前用户的员工ID
        accessible_employee_ids = [user.id for user in db.query(User).filter(
            User.role < current_role
        ).all()]
        
        if accessible_employee_ids:
            query = query.filter(
                EmployeeSalaryConfig.employee_id.in_(accessible_employee_ids)
            )
        else:
            # 如果没有可访问的员工，返回空结果
            return EmployeeSalaryConfigList(total=0, items=[])
    
    # 应用筛选条件
    if employee_id and employee_id.strip():
        try:
            employee_id_int = int(employee_id)
            query = query.filter(EmployeeSalaryConfig.employee_id == employee_id_int)
        except ValueError:
            # 如果无法转换为整数，忽略此筛选条件
            pass
    
    if department_id and department_id.strip():
        try:
            department_id_int = int(department_id)
            query = query.filter(EmployeeSalaryConfig.department_id == department_id_int)
        except ValueError:
            # 如果无法转换为整数，忽略此筛选条件
            pass
    
    if is_active is not None and is_active.strip():
        if is_active.lower() in ['true', '1', 'yes']:
            query = query.filter(EmployeeSalaryConfig.is_active.is_(True))
        elif is_active.lower() in ['false', '0', 'no']:
            query = query.filter(EmployeeSalaryConfig.is_active.is_(False))
        # 如果无法识别，忽略此筛选条件
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    configs = query.offset(skip).limit(limit).all()
    
    return EmployeeSalaryConfigList(total=total, items=[EmployeeSalaryConfigOut.from_orm(config) for config in configs])


@router.get("/my", response_model=EmployeeSalaryConfigOut)
def get_my_salary_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询当前用户的薪资配置
    所有用户都可使用
    """
    config = db.query(EmployeeSalaryConfig).filter(
        EmployeeSalaryConfig.employee_id == current_user.id,
        EmployeeSalaryConfig.is_active.is_(True)
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary config not found for current user"
        )
    
    return EmployeeSalaryConfigOut.from_orm(config)


@router.get("/{config_id}", response_model=EmployeeSalaryConfigOut)
def get_salary_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_ADMIN))
):
    """
    根据ID查询薪资配置
    仅管理员及以上权限(等级3+)可使用
    只能查看权限等级小于自身的员工
    """
    config = db.query(EmployeeSalaryConfig).filter(
        EmployeeSalaryConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary config not found"
        )
    
    # 检查权限
    if not can_access_employee(current_user, config.employee_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this salary config"
        )
    
    return EmployeeSalaryConfigOut.from_orm(config)


@router.put("/{config_id}", response_model=EmployeeSalaryConfigOut)
def update_salary_config(
    config_id: str,
    config_in: EmployeeSalaryConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_ADMIN))
):
    """
    更新员工薪资配置
    仅管理员及以上权限(等级3+)可使用
    只能修改权限等级小于自身的员工
    """
    config = db.query(EmployeeSalaryConfig).filter(
        EmployeeSalaryConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary config not found"
        )
    
    # 检查权限
    if not can_access_employee(current_user, config.employee_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this salary config"
        )
    
    # 更新字段
    update_data = config_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return EmployeeSalaryConfigOut.from_orm(config)


@router.delete("/{config_id}")
def delete_salary_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_SUPERADMIN))
):
    """
    删除员工薪资配置
    仅超级管理员(权限等级4)可使用
    """
    config = db.query(EmployeeSalaryConfig).filter(
        EmployeeSalaryConfig.id == config_id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary config not found"
        )
    
    # 软删除：设置为非激活状态
    config.is_active = False
    db.commit()
    
    return {"message": "Salary config deleted successfully"}


@router.get("/employee/{employee_id}", response_model=List[EmployeeSalaryConfigOut])
def get_employee_salary_configs(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_ADMIN))
):
    """
    查询指定员工的所有薪资配置
    仅管理员及以上权限(等级3+)可使用
    只能查看权限等级小于自身的员工
    """
    # 检查权限
    if not can_access_employee(current_user, employee_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this employee's salary configs"
        )
    
    configs = db.query(EmployeeSalaryConfig).filter(
        EmployeeSalaryConfig.employee_id == employee_id
    ).order_by(EmployeeSalaryConfig.effective_from.desc()).all()
    
    return [EmployeeSalaryConfigOut.from_orm(config) for config in configs]



