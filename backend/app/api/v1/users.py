"""Users 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user
from ...core.exceptions import not_found, conflict, bad_request
from ...core.security import hash_password, verify_password
from ...models.user import User
from ...schemas.common import ok
from ...schemas.user import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users")


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return ok(UserResponse.model_validate(current_user))


@router.put("/me")
def update_me(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前用户信息"""
    data = req.model_dump(exclude_unset=True, exclude_none=True)

    if "email" in data and data["email"] != current_user.email:
        # 检查新邮箱是否被占用
        if db.query(User).filter(User.email == data["email"]).first():
            raise conflict("Email already registered")

    if "password" in data:
        if len(data["password"]) < 6:
            raise bad_request("Password must be at least 6 characters")
        data["password_hash"] = hash_password(data.pop("password"))

    for k, v in data.items():
        setattr(current_user, k, v)

    db.commit()
    db.refresh(current_user)
    return ok(UserResponse.model_validate(current_user))
