"""统一响应格式"""
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应"""
    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class PageInfo(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class ApiPageResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: PageInfo


def ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


def fail(code: int, message: str, data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}
