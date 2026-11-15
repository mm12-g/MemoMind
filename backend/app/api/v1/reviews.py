"""Reviews API - 完整复习闭环"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ...ai.prompts import SYSTEM_AI_HELP_UNDERSTAND, USER_AI_HELP_TEMPLATE
from ...core.database import get_db
from ...core.deps import get_current_user
from ...core.exceptions import bad_request, not_found, forbidden, conflict
from ...models.card import Card
from ...models.deck import Deck
from ...models.review_log import ReviewLog
from ...models.schedule import CardSchedule
from ...models.study import StudySession
from ...models.user import User
from ...schemas.common import ok
from ...schemas.review import ReviewSubmitRequest, ReviewSubmitResponse
from ...services.ai_service import call_ai_json
from ...services.fsrs_service import (
    FSRS_STATE_LEARNING,
    FSRS_STATE_RELEARNING,
    FSRS_STATE_REVIEW,
    card_from_json,
    card_to_json,
    compute_elapsed_days,
    make_scheduler,
    review_card,
)

router = APIRouter(prefix="/reviews")


def _state_label(state: int) -> str:
    return {1: "Learning", 2: "Review", 3: "Relearning"}.get(state, "Unknown")


def _user_card_query(db: Session, current_user: User):
    """基础查询：当前用户的 Card（含 Schedule）"""
    return (
        db.query(Card, CardSchedule)
        .join(Deck, Deck.id == Card.deck_id)
        .join(CardSchedule, CardSchedule.card_id == Card.id)
        .filter(Deck.user_id == current_user.id)
    )


@router.get("/due")
def get_due_cards(
    deck_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询到期卡片（state IN 1,2,3 AND due_at <= now）"""
    now = datetime.now(timezone.utc)
    q = _user_card_query(db, current_user).filter(
        CardSchedule.state.in_([FSRS_STATE_LEARNING, FSRS_STATE_REVIEW, FSRS_STATE_RELEARNING]),
        CardSchedule.due_at <= now,
    )

    if deck_id:
        # 还要校验 deck 归属
        d = db.query(Deck).filter(Deck.id == deck_id, Deck.user_id == current_user.id).first()
        if not d:
            raise not_found("Deck")
        q = q.filter(Card.deck_id == deck_id)

    rows = q.order_by(CardSchedule.due_at).limit(limit).all()

    return ok([
        {
            "card_id": c.id,
            "deck_id": c.deck_id,
            "card_type": c.card_type,
            "front_content": c.front_content,
            "back_content": c.back_content,
            "explanation": c.explanation,
            "state": s.state,
            "due_at": s.due_at,
            "last_review_at": s.last_review_at,
        }
        for c, s in rows
    ])


@router.post("/start")
def start_session(
    deck_id: int | None = Query(default=None),
    card_id: int | None = Query(default=None),
    card_ids: str | None = Query(default=None, description="逗号分隔的 card_id 列表，置顶复习"),
    mistake_only: bool = Query(default=False, description="只复习最近 Again 过的错题"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """开始学习会话：创建 StudySession + 返回首批卡片。
    - card_id: 单张置顶
    - card_ids: 多卡置顶（逗号分隔），用于错题本批量重练
    - mistake_only: 只返回最近 Again 的错题
    - 以上都不指定则返回正常到期队列
    """
    session = StudySession(user_id=current_user.id, started_at=datetime.now(timezone.utc))
    db.add(session)
    db.commit()
    db.refresh(session)

    now = datetime.now(timezone.utc)

    def _serialize(c: Card, s: CardSchedule):
        return {
            "card_id": c.id,
            "deck_id": c.deck_id,
            "card_type": c.card_type,
            "front_content": c.front_content,
            "back_content": c.back_content,
            "explanation": c.explanation,
            "state": s.state,
        }

    # 解析置顶 card_ids（支持 card_id 单值 + card_ids 多值合并）
    pinned_ids: list[int] = []
    if card_id is not None:
        pinned_ids.append(card_id)
    if card_ids:
        for x in card_ids.split(","):
            try:
                i = int(x.strip())
                if i > 0 and i not in pinned_ids:
                    pinned_ids.append(i)
            except ValueError:
                pass

    cards = []

    # 1) 置顶卡
    if pinned_ids:
        rows = (
            db.query(Card, CardSchedule)
            .join(Deck, Deck.id == Card.deck_id)
            .join(CardSchedule, CardSchedule.card_id == Card.id)
            .filter(Card.id.in_(pinned_ids), Deck.user_id == current_user.id)
            .all()
        )
        # 按 pinned_ids 顺序排列
        order_map = {card.id: idx for idx, (card, _sch) in enumerate(rows)}
        sorted_rows = sorted(rows, key=lambda r: order_map.get(r[0].id, 999))
        cards.extend([_serialize(c, s) for c, s in sorted_rows])

    # 2) mistake_only：只取最近 Again 过的卡
    if mistake_only:
        from sqlalchemy import func as sa_func

        # 最近被 Again 过的 card_id（去重取每卡最新）
        subq = (
            db.query(
                ReviewLog.card_id,
                sa_func.max(ReviewLog.reviewed_at).label("latest"),
            )
            .filter(ReviewLog.user_id == current_user.id, ReviewLog.rating == 1)
            .group_by(ReviewLog.card_id)
            .order_by("latest", descending=True)
            .limit(50)
            .subquery()
        )
        rows = (
            db.query(Card, CardSchedule)
            .join(Deck, Deck.id == Card.deck_id)
            .join(CardSchedule, CardSchedule.card_id == Card.id)
            .join(subq, subq.c.card_id == Card.id)
            .filter(Deck.user_id == current_user.id)
            .all()
        )
        if pinned_ids:
            rows = [r for r in rows if r[0].id not in pinned_ids]
        cards.extend([_serialize(c, s) for c, s in rows])
    else:
        # 3) 正常到期队列
        q = _user_card_query(db, current_user).filter(
            CardSchedule.state.in_([FSRS_STATE_LEARNING, FSRS_STATE_REVIEW, FSRS_STATE_RELEARNING]),
            CardSchedule.due_at <= now,
        )
        if deck_id:
            q = q.filter(Card.deck_id == deck_id)
        if pinned_ids:
            q = q.filter(Card.id.notin_(pinned_ids))
        rows = q.order_by(CardSchedule.due_at).limit(50).all()
        cards.extend([_serialize(c, s) for c, s in rows])

    return ok({"session_id": session.id, "cards": cards})


@router.post("/submit/{card_id}")
def submit_review(
    card_id: int,
    req: ReviewSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交复习结果 - 核心接口（事务 + 幂等 + FSRS 调度）"""
    # --- 1. 校验卡片归属 ---
    row = (
        db.query(Card, CardSchedule)
        .join(Deck, Deck.id == Card.deck_id)
        .join(CardSchedule, CardSchedule.card_id == Card.id)
        .filter(Card.id == card_id, Deck.user_id == current_user.id)
        .first()
    )
    if not row:
        raise not_found("Card")
    card, schedule = row

    # --- 2. 幂等检查 ---
    if req.idempotency_key:
        existing = (
            db.query(ReviewLog)
            .filter(ReviewLog.idempotency_key == req.idempotency_key)
            .first()
        )
        if existing:
            # 直接返回上次结果
            return ok(ReviewSubmitResponse(
                card_id=card.id,
                new_state=existing.rating,  # 用不到实际 state，但需要结构
                new_state_label=_state_label(schedule.state),
                next_due_at=schedule.due_at,
                scheduled_days=existing.scheduled_days,
                elapsed_days=existing.elapsed_days,
            ))

    # --- 3. 加载 FSRS Card + 执行调度 ---
    now = datetime.now(timezone.utc)
    fsrs_card = card_from_json(schedule.fsrs_card_json)
    elapsed = compute_elapsed_days(fsrs_card, now)

    scheduler = make_scheduler()
    new_fsrs_card, scheduled_days = review_card(scheduler, fsrs_card, req.rating, now)

    # --- 4. 事务内更新所有表 ---
    # 4a. 更新 CardSchedule
    schedule.fsrs_card_json = card_to_json(new_fsrs_card)
    schedule.state = new_fsrs_card.state
    schedule.due_at = new_fsrs_card.due
    schedule.last_review_at = new_fsrs_card.last_review
    schedule.updated_at = now

    # 4b. 写 ReviewLog
    log = ReviewLog(
        user_id=current_user.id,
        card_id=card.id,
        session_id=req.session_id,
        rating=req.rating,
        reviewed_at=now,
        elapsed_days=elapsed,
        scheduled_days=scheduled_days,
        response_time_ms=req.response_time_ms,
        answer_text=req.answer_text,
        idempotency_key=req.idempotency_key,
    )
    db.add(log)

    # 4c. 更新 StudySession（如果有）
    if req.session_id:
        sess = db.query(StudySession).filter(
            StudySession.id == req.session_id,
            StudySession.user_id == current_user.id,
        ).first()
        if sess:
            sess.reviewed_count = (sess.reviewed_count or 0) + 1

    db.commit()

    return ok(ReviewSubmitResponse(
        card_id=card.id,
        new_state=new_fsrs_card.state,
        new_state_label=_state_label(new_fsrs_card.state),
        next_due_at=new_fsrs_card.due,
        scheduled_days=scheduled_days,
        elapsed_days=elapsed,
    ))


@router.get("/history")
def get_review_history(
    card_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询复习历史（某卡片 or 我的最近）"""
    q = db.query(ReviewLog).filter(ReviewLog.user_id == current_user.id)
    if card_id:
        # 也要校验卡片归属
        c = (
            db.query(Card)
            .join(Deck, Deck.id == Card.deck_id)
            .filter(Card.id == card_id, Deck.user_id == current_user.id)
            .first()
        )
        if not c:
            raise not_found("Card")
        q = q.filter(ReviewLog.card_id == card_id)

    logs = q.order_by(ReviewLog.reviewed_at.desc()).limit(limit).all()
    return ok([
        {
            "id": l.id,
            "card_id": l.card_id,
            "rating": l.rating,
            "reviewed_at": l.reviewed_at,
            "elapsed_days": l.elapsed_days,
            "scheduled_days": l.scheduled_days,
            "response_time_ms": l.response_time_ms,
        }
        for l in logs
    ])


@router.get("/statistics")
def get_review_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """复习统计：总共多少次、正确率、平均耗时、最常 Again 的卡等"""
    from sqlalchemy import func, case

    total = (
        db.query(func.count(ReviewLog.id))
        .filter(ReviewLog.user_id == current_user.id)
        .scalar()
        or 0
    )

    # 正确率
    correct = (
        db.query(func.count(ReviewLog.id))
        .filter(
            ReviewLog.user_id == current_user.id,
            ReviewLog.rating.in_([3, 4]),  # Good / Easy
        )
        .scalar()
        or 0
    )
    accuracy = round(correct / total * 100, 1) if total else 0.0

    # Again / Hard / Good / Easy 分布
    rating_rows = (
        db.query(ReviewLog.rating, func.count(ReviewLog.id))
        .filter(ReviewLog.user_id == current_user.id)
        .group_by(ReviewLog.rating)
        .all()
    )
    rating_map = {r: c for r, c in rating_rows}
    rating_dist = {
        "Again": rating_map.get(1, 0),
        "Hard": rating_map.get(2, 0),
        "Good": rating_map.get(3, 0),
        "Easy": rating_map.get(4, 0),
    }

    # 平均耗时（有 response_time_ms 的）
    avg_response = (
        db.query(func.avg(ReviewLog.response_time_ms))
        .filter(
            ReviewLog.user_id == current_user.id,
            ReviewLog.response_time_ms.isnot(None),
        )
        .scalar()
    )
    avg_response_ms = round(float(avg_response)) if avg_response else None

    # 复习过的不同卡片数
    unique_cards = (
        db.query(func.count(func.distinct(ReviewLog.card_id)))
        .filter(ReviewLog.user_id == current_user.id)
        .scalar()
        or 0
    )

    # 有复习的天数
    days_active = (
        db.query(func.count(func.distinct(func.date(ReviewLog.reviewed_at))))
        .filter(ReviewLog.user_id == current_user.id)
        .scalar()
        or 0
    )

    return ok({
        "total_reviews": total,
        "unique_cards_reviewed": unique_cards,
        "days_active": days_active,
        "accuracy_pct": accuracy,
        "rating_distribution": rating_dist,
        "avg_response_ms": avg_response_ms,
    })


# ---------- AI 帮助理解 ----------
def _front_preview(card: Card) -> str:
    f = card.front_content or {}
    return (
        f.get("content") or f.get("question") or f.get("word")
        or json.dumps(f, ensure_ascii=False)[:120]
    )


def _back_preview(card: Card) -> str:
    b = card.back_content or {}
    if card.card_type == "basic":
        return b.get("content", "")
    if card.card_type == "interview":
        return b.get("answer", "")
    if card.card_type == "choice":
        ans = b.get("correct_answer", [])
        exp = b.get("explanation", "")
        return f"答案: {ans} 解析: {exp}"
    if card.card_type == "vocabulary":
        return f"{b.get('cn_meaning', '')} / {b.get('en_meaning', '')}"
    return json.dumps(b, ensure_ascii=False)[:300]


@router.post("/ai-help/{card_id}")
def ai_help_understand(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 帮我理解这张卡"""
    card = (
        db.query(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id == card_id, Deck.user_id == current_user.id)
        .first()
    )
    if not card:
        raise not_found("Card")

    user_prompt = USER_AI_HELP_TEMPLATE.format(
        card_type=card.card_type,
        front=_front_preview(card),
        back=_back_preview(card),
        explanation=card.explanation or "无",
    )

    try:
        result = call_ai_json(SYSTEM_AI_HELP_UNDERSTAND, user_prompt, timeout=30)
        # 容错补字段
        result.setdefault("simple_explanation", "AI 暂时没有返回，稍后再试吧～")
        result.setdefault("analogy", "这个就像……嗯，你自己也可以想一个！")
        result.setdefault("key_points", [])
        result.setdefault("common_misconceptions", [])
        result.setdefault("memory_tip", "试着用自己的话复述一遍，讲给别人听。")
        return ok(result)
    except Exception as e:
        return ok({
            "simple_explanation": "AI 这会儿不在状态，稍后再点一次试试哦 🐾",
            "analogy": None,
            "key_points": [],
            "common_misconceptions": [],
            "memory_tip": "用费曼学习法：假装在给小白讲一遍～",
            "error": str(e)[:200],
        })
