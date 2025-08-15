"""
薪资计算引擎数据模型
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import Column, String, Text, Boolean, Date, Integer, Numeric, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, TIMESTAMP
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base


class SalaryRule(Base):
    """薪资规则表"""
    __tablename__ = "salary_rules"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, index=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # RATE, FIXED, CONDITIONAL
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # 变量定义
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # 条件规则
    fixed_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    rate_multiplier: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SalaryCalculationBatch(Base):
    """薪资计算批次表"""
    __tablename__ = "salary_calculation_batches"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, index=True, server_default=func.gen_random_uuid())
    batch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    calculation_period: Mapped[str] = mapped_column(String(20), nullable=False)  # MONTHLY, WEEKLY, CUSTOM
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    total_employees: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    error_log: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关系
    creator = relationship("User", back_populates="salary_batches")
    results = relationship("SalaryCalculationResult", back_populates="batch")


class SalaryCalculationResult(Base):
    """薪资计算结果表"""
    __tablename__ = "salary_calculation_results"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, index=True, server_default=func.gen_random_uuid())
    batch_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("salary_calculation_batches.id"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))
    total_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal('0'))
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal('0'))
    rule_results: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))
    deductions: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CALCULATED", index=True)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关系
    batch = relationship("SalaryCalculationBatch", back_populates="results")
    employee = relationship("User", foreign_keys=[employee_id])
    approver = relationship("User", foreign_keys=[approved_by])


class EmployeeSalaryConfig(Base):
    """员工薪资配置表"""
    __tablename__ = "employee_salary_configs"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, index=True, server_default=func.gen_random_uuid())
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=Decimal('0'))
    overtime_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal('1.5'))
    department_id: Mapped[Optional[int]] = mapped_column(Integer)
    position: Mapped[Optional[str]] = mapped_column(String(100))
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关系
    employee = relationship("User", back_populates="salary_configs")


class DeductionConfig(Base):
    """扣除项配置表"""
    __tablename__ = "deduction_configs"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, index=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    deduction_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # PERCENTAGE, FIXED, CONDITIONAL
    percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    fixed_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    formula: Mapped[Optional[str]] = mapped_column(Text)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0'))
    max_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# Pydantic模型用于API
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class EmployeeSalaryConfigCreate(BaseModel):
    """创建员工薪资配置的请求模型"""
    employee_id: int = Field(..., description="员工ID")
    base_salary: Decimal = Field(Decimal('0'), description="基本工资")
    hourly_rate: Decimal = Field(Decimal('0'), description="时薪")
    overtime_rate: Decimal = Field(Decimal('1.5'), description="加班倍率")
    department_id: Optional[int] = Field(None, description="部门ID")
    position: Optional[str] = Field(None, description="职位")
    effective_from: date = Field(default_factory=date.today, description="生效日期")
    effective_to: Optional[date] = Field(None, description="失效日期")
    is_active: bool = Field(True, description="是否激活")

class EmployeeSalaryConfigUpdate(BaseModel):
    """更新员工薪资配置的请求模型"""
    base_salary: Optional[Decimal] = Field(None, description="基本工资")
    hourly_rate: Optional[Decimal] = Field(None, description="时薪")
    overtime_rate: Optional[Decimal] = Field(None, description="加班倍率")
    department_id: Optional[int] = Field(None, description="部门ID")
    position: Optional[str] = Field(None, description="职位")
    effective_from: Optional[date] = Field(None, description="生效日期")
    effective_to: Optional[date] = Field(None, description="失效日期")
    is_active: Optional[bool] = Field(None, description="是否激活")

class EmployeeSalaryConfigOut(BaseModel):
    """员工薪资配置的响应模型"""
    id: UUID
    employee_id: int
    base_salary: Decimal
    hourly_rate: Decimal
    overtime_rate: Decimal
    department_id: Optional[int]
    position: Optional[str]
    effective_from: date
    effective_to: Optional[date]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EmployeeSalaryConfigList(BaseModel):
    """员工薪资配置列表的响应模型"""
    total: int
    items: list[EmployeeSalaryConfigOut]
