"""依赖注入 - FastAPI Depends"""
from typing import Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from .database import get_db
from .exceptions import unauthorized
from .security import decode_access_token
from ..models.user import User


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
) -> User:
    """从 Authorization Header 解析 JWT 并获取当前用户"""
    if not authorization:
        raise unauthorized("Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise unauthorized("Invalid Authorization format, expected 'Bearer <token>'")

    payload = decode_access_token(parts[1])
    if not payload or "sub" not in payload:
        raise unauthorized("Invalid or expired token")

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise unauthorized("Invalid token subject")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise unauthorized("User not found")

    return user


def get_optional_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
) -> Optional[User]:
    """可选的用户认证 - 无 Token 时返回 None"""
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    payload = decode_access_token(parts[1])
    if not payload or "sub" not in payload:
        return None

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None

    return db.query(User).filter(User.id == user_id).first()
