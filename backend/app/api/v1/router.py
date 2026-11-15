"""V1 API 汇总路由"""
from fastapi import APIRouter

from . import auth, users, decks, cards, tags, reviews, goals, analytics, ai, practice
from ...services import associate_service, feynman_service

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, tags=["auth"])
router.include_router(users.router, tags=["users"])
router.include_router(decks.router, tags=["decks"])
router.include_router(cards.router, tags=["cards"])
router.include_router(tags.router, tags=["tags"])
router.include_router(reviews.router, tags=["reviews"])
router.include_router(goals.router, tags=["goals"])
router.include_router(analytics.router, tags=["analytics"])
router.include_router(ai.router, tags=["ai"])
router.include_router(practice.router, tags=["practice"])
router.include_router(associate_service.router, prefix="/cards/{card_id}", tags=["associate"])
router.include_router(feynman_service.router, tags=["feynman"])


@router.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    from ...core.config import settings

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "app": settings.app_name,
            "env": settings.app_env,
            "status": "healthy",
        },
    }
