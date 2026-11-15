"""FSRS Service - 封装 fsrs.Scheduler + Card 序列化 + 状态同步"""
from datetime import datetime, timezone
from typing import Optional

from fsrs import Card, Rating, Scheduler, State

from ..core.config import settings

# FSRS 状态枚举
FSRS_STATE_LEARNING = State.Learning.value   # 1
FSRS_STATE_REVIEW = State.Review.value       # 2
FSRS_STATE_RELEARNING = State.Relearning.value  # 3

RATING_MAP = {
    1: Rating.Again,
    2: Rating.Hard,
    3: Rating.Good,
    4: Rating.Easy,
}


def make_scheduler() -> Scheduler:
    """创建 Scheduler 实例。
    可通过 p 自定义参数（如 target_retention 来自 LearningGoal）"""
    # P1 阶段先用默认参数
    # 目标 retention 默认 0.9，可在 P3 后根据用户 LearningGoal 调整
    return Scheduler()


def new_card() -> Card:
    """创建新卡片的 FSRS Card 对象"""
    return Card()


def card_from_json(data: dict) -> Card:
    """从 db 的 fsrs_card_json 还原 Card 对象"""
    return Card.from_dict(data)


def card_to_json(card: Card) -> dict:
    """序列化 Card 为 JSON（存入 db）"""
    return card.to_dict()


def review_card(
    scheduler: Scheduler,
    card: Card,
    rating: int,
    now: Optional[datetime] = None,
) -> tuple[Card, int]:
    """执行一次复习，返回 (新 Card, 计划间隔天数)

    rating: 1=Again, 2=Hard, 3=Good, 4=Easy
    返回的 计划间隔天数 = (new_due - now).days（四舍五入）
    """
    if rating not in RATING_MAP:
        raise ValueError(f"Invalid rating: {rating}, must be 1-4")

    now = now or datetime.now(timezone.utc)
    new_card, _log = scheduler.review_card(card, RATING_MAP[rating], now)

    # 计算 scheduled_days
    scheduled_days = round((new_card.due - now).total_seconds() / 86400)

    return new_card, scheduled_days


def compute_elapsed_days(card: Card, now: datetime) -> Optional[int]:
    """计算 elapsed_days（实际间隔天数）。首次复习返回 None"""
    if card.last_review is None:
        return None
    return round((now - card.last_review).total_seconds() / 86400)
