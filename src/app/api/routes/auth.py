from datetime import timedelta
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.app.api.deps import get_db, require_role
from src.app.core.security import create_access_token, get_password_hash, verify_password
from src.app.models.user import TokenOut, User, UserCreate, UserLogin, UserOut
from src.app.models.salary_engine import EmployeeSalaryConfig


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, cast(str, user.password_hash)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "username": user.username},
        expires_delta=timedelta(minutes=60),
    )
    return TokenOut(access_token=access_token)


# 标准 OAuth2 密码模式（表单）：tokenUrl 与依赖保持一致
@router.post("/token", response_model=TokenOut)
def issue_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if user is None or not verify_password(form_data.password, cast(str, user.password_hash)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "username": user.username},
        expires_delta=timedelta(minutes=60),
    )
    return TokenOut(access_token=access_token)


@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == user_in.username).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    
    try:
        user = User(
            username=user_in.username,
            email=user_in.email,
            full_name=user_in.full_name,
            password_hash=get_password_hash(user_in.password),
            role=user_in.role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 为新注册用户添加默认薪资配置
        salary_config = EmployeeSalaryConfig(
            employee_id=user.id,
            base_salary=0,  # 默认基本工资为0
            hourly_rate=20,  # 默认时薪为0
            overtime_rate=1.5,  # 默认加班倍率为1.5
            is_active=True
        )
        db.add(salary_config)
        db.commit()
        
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(require_role(1))):
    return current_user


