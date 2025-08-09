from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, SmallInteger, func
from sqlalchemy.orm import validates
from pydantic import BaseModel, Field

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    password_hash = Column(String, nullable=False)
    # 角色：1=非正式员工，2=正式员工，3=管理员，4=超级管理员（0 代表未登录，不入库）
    role = Column(SmallInteger, nullable=False, default=2)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    @validates("role")
    def validate_role(self, key, value):  # type: ignore[no-untyped-def]
        if value is None or not (1 <= int(value) <= 4):
            raise ValueError("role must be between 1 and 4")
        return int(value)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: int = 2


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: int
    is_active: bool

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


