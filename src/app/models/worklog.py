from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, String, Text, DECIMAL, func, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from app.db.base import Base


class WorkLog(Base):
    __tablename__ = 'worklogs'
    
    entry_id = Column(PGUUID(as_uuid=True), primary_key=True, index=True, server_default=func.gen_random_uuid())
    employee_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey('projects.id'), nullable=False, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    hours = Column(DECIMAL(4,2), nullable=False)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # 关系定义
    employee = relationship("User", back_populates="worklogs")
    project = relationship("Project", back_populates="worklogs")


# Pydantic models for API
class WorkLogBase(BaseModel):
    employee_id: int = Field(description="员工ID")
    date: datetime = Field(description="工作日期")
    project_id: UUID = Field(description="项目ID")
    task_type: str = Field(min_length=1, max_length=50, description="任务类型")
    hours: float = Field(gt=0, le=24, description="工时")
    remarks: Optional[str] = Field(None, description="备注")


class WorkLogCreate(WorkLogBase):
    pass


class WorkLogUpdate(BaseModel):
    employee_id: Optional[int] = Field(None, description="员工ID")
    date: Optional[datetime] = Field(None, description="工作日期")
    project_id: Optional[UUID] = Field(None, description="项目ID")
    task_type: Optional[str] = Field(None, min_length=1, max_length=50, description="任务类型")
    hours: Optional[float] = Field(None, gt=0, le=24, description="工时")
    remarks: Optional[str] = Field(None, description="备注")


class WorkLogOut(WorkLogBase):
    entry_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkLogList(BaseModel):
    worklogs: list[WorkLogOut]
    total: int
    page: int
    size: int 