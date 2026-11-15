"""Analytics Service - 学习统计"""
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from sqlalchemy import func, case, select, Integer, and_, text, cast
from sqlalchemy.orm import Session

from ..models.card import Card
from ..models.deck import Deck
from ..models.review_log import ReviewLog
from ..models.schedule import CardSchedule
from ..models.study import StudySession, LearningGoal
from ..models.user import User


def _start_of_day(dt: datetime) -> datetime:
    """取 dt 所在天的 UTC 0 点"""
    return dt.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def get_dashboard_stats(db: Session, user_id: int) -> dict:
    """Dashboard 首页统计卡片"""
    now = datetime.now(timezone.utc)
    today_start = _start_of_day(now)
    tomorrow_start = today_start + timedelta(days=1)
    week_ago = today_start - timedelta(days=6)

    # 到期卡片数
    due_count = (
        db.query(func.count(CardSchedule.card_id))
        .join(Card, Card.id == CardSchedule.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(
            Deck.user_id == user_id,
            CardSchedule.state.in_([1, 2, 3]),
            CardSchedule.due_at <= now,
        )
        .scalar()
        or 0
    )

    # 今日新增卡片（created_at 在今天）
    new_today = (
        db.query(func.count(Card.id))
        .join(Deck, Deck.id == Card.deck_id)
        .filter(
            Deck.user_id == user_id,
            Card.created_at >= today_start,
            Card.created_at < tomorrow_start,
        )
        .scalar()
        or 0
    )

    # 今日已复习
    reviewed_today = (
        db.query(func.count(ReviewLog.id))
        .filter(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= today_start,
            ReviewLog.reviewed_at < tomorrow_start,
        )
        .scalar()
        or 0
    )

    # 已掌握：state=Review 且 stability > 21（稳定 3 周以上）
    mastered_count = (
        db.query(func.count(CardSchedule.card_id))
        .join(Card, Card.id == CardSchedule.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(
            Deck.user_id == user_id,
            CardSchedule.state == 2,
        )
        .scalar()
        or 0
    )
    # 更精确：从 fsrs_card_json 里取 stability
    rows = (
        db.query(CardSchedule)
        .join(Card, Card.id == CardSchedule.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Deck.user_id == user_id)
        .all()
    )
    mastered = 0
    for s in rows:
        data = s.fsrs_card_json or {}
        stab = data.get("stability")
        if stab is not None and stab > 21:
            mastered += 1

    # 连续学习天数
    review_days = (
        db.query(func.date(ReviewLog.reviewed_at))
        .filter(ReviewLog.user_id == user_id)
        .distinct()
        .all()
    )
    review_dates = {r[0] for r in review_days}

    today = datetime.now(timezone.utc).date()
    # 如果今天没复习，从昨天开始算 streak
    cursor = today if today in review_dates else today - timedelta(days=1)
    streak = 0
    while cursor in review_dates:
        streak += 1
        cursor -= timedelta(days=1)

    # 今日正确率：Good + Easy / 总复习
    correct_today = (
        db.query(func.count(ReviewLog.id))
        .filter(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= today_start,
            ReviewLog.reviewed_at < tomorrow_start,
            ReviewLog.rating.in_([3, 4]),
        )
        .scalar()
        or 0
    )
    accuracy = round(correct_today / reviewed_today * 100, 1) if reviewed_today else None

    return {
        "due_today": due_count,
        "new_today": new_today,
        "reviewed_today": reviewed_today,
        "mastered_count": mastered,
        "streak_days": streak,
        "today_accuracy": accuracy,
    }


def get_trend(db: Session, user_id: int, days: int = 7) -> dict:
    """学习趋势：近 N 天每天的复习数、新增数、正确率"""
    now = datetime.now(timezone.utc)
    start_date = _start_of_day(now) - timedelta(days=days - 1)

    # 构建日期序列（补全 0 天）
    day_list = [(start_date + timedelta(days=i)).date() for i in range(days)]

    # 复习数
    review_rows = (
        db.query(
            func.date(ReviewLog.reviewed_at).label("d"),
            func.count(ReviewLog.id).label("cnt"),
        )
        .filter(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= start_date,
        )
        .group_by("d")
        .all()
    )
    review_map = {r[0]: r[1] for r in review_rows}

    # 新增数
    new_rows = (
        db.query(
            func.date(Card.created_at).label("d"),
            func.count(Card.id).label("cnt"),
        )
        .join(Deck, Deck.id == Card.deck_id)
        .filter(
            Deck.user_id == user_id,
            Card.created_at >= start_date,
        )
        .group_by("d")
        .all()
    )
    new_map = {r[0]: r[1] for r in new_rows}

    # 正确率
    acc_rows = (
        db.query(
            func.date(ReviewLog.reviewed_at).label("d"),
            func.avg(case((ReviewLog.rating.in_([3, 4]), 1.0), else_=0.0)).label("acc"),
        )
        .filter(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= start_date,
        )
        .group_by("d")
        .all()
    )
    acc_map = {r[0]: round((r[1] or 0) * 100, 1) for r in acc_rows}

    items = []
    for d in day_list:
        items.append({
            "date": d.isoformat(),
            "reviewed": review_map.get(d, 0),
            "new": new_map.get(d, 0),
            "accuracy": acc_map.get(d, None),
        })

    return {"days": days, "items": items}


def get_deck_stats(db: Session, user_id: int) -> list:
    """各知识库掌握情况"""
    decks = (
        db.query(Deck)
        .filter(Deck.user_id == user_id)
        .order_by(Deck.updated_at.desc())
        .all()
    )

    result = []
    for deck in decks:
        # 卡片总数
        total = (
            db.query(func.count(Card.id))
            .filter(Card.deck_id == deck.id)
            .scalar()
            or 0
        )

        # 各 state 数量
        state_rows = (
            db.query(
                CardSchedule.state,
                func.count(CardSchedule.card_id),
            )
            .join(Card, Card.id == CardSchedule.card_id)
            .filter(Card.deck_id == deck.id)
            .group_by(CardSchedule.state)
            .all()
        )
        state_map = {s: c for s, c in state_rows}

        # 已掌握（stability > 21）
        cards_in_deck = (
            db.query(CardSchedule.fsrs_card_json)
            .join(Card, Card.id == CardSchedule.card_id)
            .filter(Card.deck_id == deck.id)
            .all()
        )
        mastered = 0
        for (j,) in cards_in_deck:
            if j and j.get("stability") is not None and j.get("stability", 0) > 21:
                mastered += 1

        result.append({
            "deck_id": deck.id,
            "name": deck.name,
            "card_count": total,
            "learning": state_map.get(1, 0),
            "review": state_map.get(2, 0),
            "relearning": state_map.get(3, 0),
            "mastered": mastered,
            "mastered_pct": round(mastered / total * 100, 1) if total else 0,
            "category": deck.category,
        })

    return result


def get_retention(db: Session, user_id: int) -> dict:
    """记忆保持率估算：基于 FSRS stability，计算不同天数后的预估保持率"""
    now = datetime.now(timezone.utc)

    schedules = (
        db.query(CardSchedule.fsrs_card_json)
        .join(Card, Card.id == CardSchedule.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Deck.user_id == user_id)
        .all()
    )

    # 汇总 stability
    stabilities = []
    for (j,) in schedules:
        if j and j.get("stability") is not None:
            stabilities.append(j.get("stability"))

    if not stabilities:
        return {
            "total_cards": 0,
            "avg_stability": None,
            "avg_retention_1d": None,
            "avg_retention_7d": None,
            "avg_retention_30d": None,
        }

    import math

    avg_s = sum(stabilities) / len(stabilities)

    # FSRS 保持率公式: R = exp(-D / S)，D 是 elapsed days，S 是 stability
    def retention_at(days: int) -> float:
        total = 0.0
        count = 0
        for s in stabilities:
            if s > 0:
                total += math.exp(-days / s)
                count += 1
        return round(total / count * 100, 1) if count else 0.0

    return {
        "total_cards": len(stabilities),
        "avg_stability": round(avg_s, 1),
        "avg_retention_1d": retention_at(1),
        "avg_retention_7d": retention_at(7),
        "avg_retention_30d": retention_at(30),
    }


def get_weak_points(db: Session, user_id: int, limit: int = 10) -> list:
    """薄弱知识点：经常 Again 的卡片"""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    # 近 30 天 Again 次数多的卡片
    rows = (
        db.query(
            ReviewLog.card_id,
            func.count(ReviewLog.id).label("again_cnt"),
        )
        .filter(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= start,
            ReviewLog.rating == 1,  # Again
        )
        .group_by(ReviewLog.card_id)
        .order_by(func.count(ReviewLog.id).desc())
        .limit(limit)
        .all()
    )
    if not rows:
        return []

    card_ids = [r[0] for r in rows]
    cnt_map = {r[0]: r[1] for r in rows}

    cards = (
        db.query(Card, Deck.name)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id.in_(card_ids))
        .all()
    )

    result = []
    for card, deck_name in cards:
        # 取卡片当前 state / stability
        sched = (
            db.query(CardSchedule)
            .filter(CardSchedule.card_id == card.id)
            .first()
        )
        stab = (sched.fsrs_card_json or {}).get("stability") if sched else None

        result.append({
            "card_id": card.id,
            "deck_id": card.deck_id,
            "deck_name": deck_name,
            "card_type": card.card_type,
            "front_preview": (
                card.front_content.get("content")
                or card.front_content.get("question")
                or card.front_content.get("word")
                or str(card.front_content)[:60]
            ),
            "again_count": cnt_map.get(card.id, 0),
            "current_stability": stab,
            "state": sched.state if sched else None,
        })

    return result
