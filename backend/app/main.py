"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.exceptions import register_exception_handlers
from .api.v1.router import router as api_v1_router

app = FastAPI(
    title=settings.app_name,
    description="MemoMind - AI 智能记忆平台",
    version="0.1.0",
)

# ----- CORS -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- 路由 -----
app.include_router(api_v1_router)

# ----- 异常处理器 -----
register_exception_handlers(app)


@app.on_event("startup")
async def _startup():
    print(f"[MemoMind] Starting in '{settings.app_env}' mode...")
    print(f"[MemoMind] Database: {settings.database_url}")
