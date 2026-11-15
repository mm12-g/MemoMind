"""Goals API - 学习目标 + 用户注册时自动创建"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user
from ...models.card import Card
from ...models.deck import Deck
from ...models.review_log import ReviewLog
from ...models.schedule import CardSchedule
from ...models.study import LearningGoal
from ...models.user import User
from ...schemas.common import ok

router = APIRouter(prefix="/goals")


def ensure_goal(db: Session, user_id: int) -> LearningGoal:
    """确保用户有一条 LearningGoal（注册时可能漏了）"""
    goal = db.query(LearningGoal).filter(LearningGoal.user_id == user_id).first()
    if not goal:
        goal = LearningGoal(user_id=user_id)
        db.add(goal)
        db.commit()
        db.refresh(goal)
    return goal


@router.get("")
def get_goal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = ensure_goal(db, current_user.id)
    return ok({
        "id": goal.id,
        "user_id": goal.user_id,
        "daily_new_limit": goal.daily_new_limit,
        "daily_review_limit": goal.daily_review_limit,
        "daily_minutes_goal": goal.daily_minutes_goal,
        "desired_retention": goal.desired_retention,
    })


@router.put("")
def update_goal(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = ensure_goal(db, current_user.id)
    allowed = {"daily_new_limit", "daily_review_limit", "daily_minutes_goal", "desired_retention"}
    for k, v in body.items():
        if k in allowed:
            setattr(goal, k, v)
    db.commit()
    db.refresh(goal)
    return ok({
        "daily_new_limit": goal.daily_new_limit,
        "daily_review_limit": goal.daily_review_limit,
        "daily_minutes_goal": goal.daily_minutes_goal,
        "desired_retention": goal.desired_retention,
    })


@router.get("/daily")
def get_daily_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """今日目标完成情况"""
    goal = ensure_goal(db, current_user.id)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    # 今日新增
    new_today = (
        db.query(func.count(Card.id))
        .join(Deck, Deck.id == Card.deck_id)
        .filter(
            Deck.user_id == current_user.id,
            Card.created_at >= today_start,
            Card.created_at < tomorrow_start,
        )
        .scalar()
        or 0
    )

    # 今日复习数
    reviewed_today = (
        db.query(func.count(ReviewLog.id))
        .filter(
            ReviewLog.user_id == current_user.id,
            ReviewLog.reviewed_at >= today_start,
            ReviewLog.reviewed_at < tomorrow_start,
        )
        .scalar()
        or 0
    )

    # 今日到期总数（作为 review 目标参考）
    due_total = (
        db.query(func.count(CardSchedule.card_id))
        .join(Card, Card.id == CardSchedule.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(
            Deck.user_id == current_user.id,
            CardSchedule.state.in_([1, 2, 3]),
            CardSchedule.due_at >= today_start,
            CardSchedule.due_at < tomorrow_start,
        )
        .scalar()
        or 0
    )

    # 今日正确率
    correct_today = (
        db.query(func.count(ReviewLog.id))
        .filter(
            ReviewLog.user_id == current_user.id,
            ReviewLog.reviewed_at >= today_start,
            ReviewLog.reviewed_at < tomorrow_start,
            ReviewLog.rating.in_([3, 4]),
        )
        .scalar()
        or 0
    )
    accuracy = round(correct_today / reviewed_today * 100, 1) if reviewed_today else 0.0

    return ok({
        "goals": {
            "daily_new_limit": goal.daily_new_limit,
            "daily_review_limit": goal.daily_review_limit,
            "daily_minutes_goal": goal.daily_minutes_goal,
        },
        "actual": {
            "new_today": new_today,
            "reviewed_today": reviewed_today,
            "accuracy_pct": accuracy,
            "due_today": due_total,
        },
        "progress": {
            "new_pct": min(round(new_today / max(goal.daily_new_limit, 1) * 100, 1), 100),
            "review_pct": min(round(reviewed_today / max(goal.daily_review_limit, 1) * 100, 1), 100),
        },
    })
