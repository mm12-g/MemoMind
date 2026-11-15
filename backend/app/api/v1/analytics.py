"""Analytics API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user
from ...models.user import User
from ...schemas.common import ok
from ...services.analytics_service import (
    get_dashboard_stats,
    get_trend,
    get_deck_stats,
    get_weak_points,
    get_retention,
)

router = APIRouter(prefix="/analytics")


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ok(get_dashboard_stats(db, current_user.id))


@router.get("/trend")
def trend(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ok(get_trend(db, current_user.id, days))


@router.get("/decks")
def deck_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ok(get_deck_stats(db, current_user.id))


@router.get("/weak-points")
def weak_points(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ok(get_weak_points(db, current_user.id, limit))


@router.get("/retention")
def retention(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """记忆保持率估算：基于 FSRS stability"""
    return ok(get_retention(db, current_user.id))
