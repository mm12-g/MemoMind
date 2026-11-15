"""Auth 路由"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.exceptions import bad_request, conflict, unauthorized
from ...core.security import create_access_token, hash_password, verify_password
from ...models.study import LearningGoal
from ...models.user import User
from ...schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from ...schemas.common import ok
from ...core.config import settings

router = APIRouter(prefix="/auth")


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册 - 同时创建默认 LearningGoal"""
    if db.query(User).filter(User.email == req.email).first():
        raise conflict("Email already registered")

    user = User(
        email=req.email,
        username=req.username,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.flush()  # 先拿到 user.id

    # 自动创建默认学习目标
    goal = LearningGoal(user_id=user.id)
    db.add(goal)

    db.commit()
    db.refresh(user)

    return ok(RegisterResponse(
        user_id=user.id,
        email=user.email,
        username=user.username,
    ))


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise unauthorized("Invalid email or password")

    if user.status != "active":
        raise bad_request("Account is not active")

    token = create_access_token(user.id)
    return ok(TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    ))
