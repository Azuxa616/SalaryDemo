from typing import Callable, Generator, cast

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.base import SessionLocal
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = str(payload.get("sub")) if payload.get("sub") is not None else ""
    except (JWTError, ValueError):
        raise credentials_exception
    if not user_id:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
   
    if user:
        # 确保属性已加载
        _ = user.role  # 触发加载
        
    if user is None:
        raise credentials_exception
    # SQLAlchemy 的 InstrumentedAttribute 在类型检查中不可用作布尔值，显式转换
    is_active: bool = cast(bool, user.is_active)
    if not is_active:
        raise credentials_exception
    
    return user


def require_role(min_role: int) -> Callable[[User], User]:
    def _require(user: User = Depends(get_current_user)) -> User:
        user_role: int = cast(int, user.role)
        if user_role < min_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _require


