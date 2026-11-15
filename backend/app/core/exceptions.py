"""全局自定义异常 + 异常处理器"""
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """MemoMind 统一业务异常"""

    def __init__(
        self,
        code: int = 400,
        message: str = "Bad Request",
        detail: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


# ---------- 常用异常快捷函数 ----------

def not_found(resource: str = "Resource", detail: Any = None) -> AppException:
    return AppException(404, f"{resource} not found", detail)


def unauthorized(message: str = "Unauthorized") -> AppException:
    return AppException(401, message)


def forbidden(message: str = "Forbidden") -> AppException:
    return AppException(403, message)


def bad_request(message: str = "Bad Request", detail: Any = None) -> AppException:
    return AppException(400, message, detail)


def conflict(message: str = "Conflict", detail: Any = None) -> AppException:
    return AppException(409, message, detail)


# ---------- 注册异常处理器 ----------

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "message": exc.message, "data": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # 生产环境不暴露详情
        from .config import settings

        detail = None if settings.is_prod else str(exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal Server Error",
                "data": detail,
            },
        )

    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err["loc"])
            errors.append({"field": loc, "msg": err["msg"], "type": err["type"]})
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": "Validation Failed", "data": errors},
        )
