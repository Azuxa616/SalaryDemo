from sqlalchemy import Column, Integer, String, Float
from app.db.base import Base
from pydantic import BaseModel

class WorkLog(Base):
    __tablename__ = 'worklogs'
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, index=True)
    task_type = Column(String, index=True)
    hours = Column(Float)
    project = Column(String)

class WorkLogIn(BaseModel):
    employee_id: int
    task_type: str
    hours: float
    project: str

class WorkLogOut(WorkLogIn):
    id: int
    class Config:
        from_attributes = True 