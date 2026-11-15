"""Practice API - 面试专项 / 考试 / 英语"""
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user
from ...core.exceptions import bad_request, not_found
from ...models.card import Card
from ...models.deck import Deck
from ...models.practice import ExamRecord, InterviewSession
from ...models.review_log import ReviewLog
from ...models.user import User
from ...schemas.common import ok
from ...services.ai_service import evaluate_answer  # 复用 P5 的 AI 评分

router = APIRouter(prefix="/practice")


# ============================================================
# 通用：抽取卡片
# ============================================================

def _draw_cards(
    db: Session,
    user_id: int,
    *,
    deck_id: int | None = None,
    card_type: str | None = None,
    count: int = 10,
) -> list[Card]:
    q = db.query(Card).join(Deck, Deck.id == Card.deck_id).filter(Deck.user_id == user_id)
    if deck_id:
        q = q.filter(Card.deck_id == deck_id)
    if card_type:
        q = q.filter(Card.card_type == card_type)

    all_cards = q.all()
    if len(all_cards) <= count:
        return all_cards
    return random.sample(all_cards, count)


# ============================================================
# 1) 面试专项
# ============================================================

@router.post("/interview/start")
def start_interview(
    deck_id: int | None = Query(default=None),
    count: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """开始面试训练 → 抽取 interview 卡片"""
    cards = _draw_cards(
        db, current_user.id,
        deck_id=deck_id, card_type="interview", count=count,
    )
    if not cards:
        raise bad_request("没有 interview 类型的卡片，请先去 AI 工作台或手动创建")

    session = InterviewSession(
        user_id=current_user.id,
        deck_id=deck_id,
        card_ids=[c.id for c in cards],
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return ok({
        "session_id": session.id,
        "cards": [
            {
                "card_id": c.id,
                "question": (c.front_content or {}).get("question"),
                "keywords": (c.front_content or {}).get("keywords", []),
                "difficulty": (c.back_content or {}).get("difficulty"),
            }
            for c in cards
        ],
    })


@router.post("/interview/evaluate")
def evaluate_interview_answer(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 评分面试回答"""
    card_id = body.get("card_id")
    user_answer = body.get("user_answer")

    card = (
        db.query(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id == card_id, Deck.user_id == current_user.id)
        .first()
    )
    if not card:
        raise not_found("Card")

    question = (card.front_content or {}).get("question", "")
    ref_answer = (card.back_content or {}).get("answer", "")

    result = evaluate_answer(question, ref_answer, user_answer)
    return ok(result)


@router.post("/interview/{session_id}/complete")
def complete_interview(
    session_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """结束面试会话"""
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise not_found("Session")

    scores = body.get("scores", [])
    if scores:
        session.scores = scores
        total = sum(s.get("score", 0) for s in scores)
        session.avg_score = round(total / len(scores), 1) if scores else 0
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    return ok({"session_id": session.id, "avg_score": session.avg_score})


# ============================================================
# 2) 模拟考试
# ============================================================

@router.post("/exam/start")
def start_exam(
    deck_id: int | None = Query(default=None),
    count: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """开始模拟考试 → 抽取 choice 卡片"""
    cards = _draw_cards(
        db, current_user.id,
        deck_id=deck_id, card_type="choice", count=count,
    )
    if not cards:
        raise bad_request("没有 choice 类型的卡片")

    record = ExamRecord(
        user_id=current_user.id,
        deck_id=deck_id,
        card_ids=[c.id for c in cards],
        total_count=len(cards),
        started_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ok({
        "exam_id": record.id,
        "total_count": record.total_count,
        "cards": [
            {
                "card_id": c.id,
                "question": (c.front_content or {}).get("question"),
                "options": (c.front_content or {}).get("options", []),
                "is_multiple": (c.front_content or {}).get("is_multiple", False),
            }
            for c in cards
        ],
    })


@router.post("/exam/{exam_id}/submit")
def submit_exam(
    exam_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交考试答卷"""
    record = db.query(ExamRecord).filter(
        ExamRecord.id == exam_id, ExamRecord.user_id == current_user.id,
    ).first()
    if not record:
        raise not_found("Exam")
    if record.submitted_at:
        raise bad_request("考试已提交")

    submissions: list[dict] = body.get("answers", [])
    answers: list[dict] = []
    correct_count = 0

    for sub in submissions:
        card_id = sub.get("card_id")
        user_ans = sub.get("answer", [])

        card = db.query(Card).filter(Card.id == card_id).first()
        if not card:
            continue

        correct_ans = (card.back_content or {}).get("correct_answer", [])
        is_correct = sorted(user_ans) == sorted(correct_ans)
        if is_correct:
            correct_count += 1

        answers.append({
            "card_id": card_id,
            "answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": (card.back_content or {}).get("explanation"),
            "question": (card.front_content or {}).get("question"),
            "options": (card.front_content or {}).get("options", []),
        })

    now = datetime.now(timezone.utc)
    duration = None
    if record.started_at:
        duration = round((now - record.started_at).total_seconds())

    record.answers = answers
    record.correct_count = correct_count
    record.score = round(correct_count / record.total_count * 100, 1) if record.total_count else 0
    record.duration_seconds = duration
    record.submitted_at = now
    db.commit()

    return ok({
        "exam_id": record.id,
        "total": record.total_count,
        "correct": correct_count,
        "score": record.score,
        "duration_seconds": duration,
        "details": answers,
    })


@router.get("/exams")
def list_exams(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(ExamRecord)
        .filter(ExamRecord.user_id == current_user.id)
        .order_by(ExamRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return ok([
        {
            "id": r.id,
            "total_count": r.total_count,
            "correct_count": r.correct_count,
            "score": r.score,
            "duration_seconds": r.duration_seconds,
            "created_at": r.created_at,
            "submitted_at": r.submitted_at,
        }
        for r in records
    ])


# ============================================================
# 3) 英语专项 (Vocabulary 听写/选择训练，复用 choice 卡片)
# ============================================================

@router.post("/vocab/start")
def start_vocab(
    deck_id: int | None = Query(default=None),
    mode: str = Query(default="spelling", description="spelling(拼写) / choice(选择)"),
    count: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """英语训练：抽取 vocabulary 卡片"""
    cards = _draw_cards(
        db, current_user.id,
        deck_id=deck_id, card_type="vocabulary", count=count,
    )
    if not cards:
        raise bad_request("没有 vocabulary 类型的卡片")

    return ok({
        "mode": mode,
        "count": len(cards),
        "cards": [
            {
                "card_id": c.id,
                "word": (c.front_content or {}).get("word"),
                "phonetic": (c.front_content or {}).get("phonetic"),
                "cn_meaning": (c.back_content or {}).get("cn_meaning"),
                "en_meaning": (c.back_content or {}).get("en_meaning"),
                "examples": (c.back_content or {}).get("examples", []),
            }
            for c in cards
        ],
    })


# ============================================================
# 4) 错题本
# ============================================================

@router.get("/mistakes")
def list_mistakes(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """错题列表：最近被标记为 Again (rating=1) 的卡片，按时间倒序"""
    from sqlalchemy import func

    rows = (
        db.query(
            ReviewLog,
            Card,
            Deck.name,
        )
        .join(Card, Card.id == ReviewLog.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(
            ReviewLog.user_id == current_user.id,
            ReviewLog.rating == 1,  # Again
        )
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(limit * 3)  # 多取点去重
        .all()
    )

    # 去重：每张卡只保留最近一次 Again
    seen: dict[int, dict] = {}
    for log, card, deck_name in rows:
        if card.id in seen:
            continue
        fc = card.front_content or {}
        front_preview = (
            fc.get("content") or fc.get("question") or fc.get("word")
            or str(fc)[:60]
        )
        seen[card.id] = {
            "card_id": card.id,
            "deck_id": card.deck_id,
            "deck_name": deck_name,
            "card_type": card.card_type,
            "front_preview": front_preview,
            "reviewed_at": log.reviewed_at.isoformat(),
            "user_answer": log.answer_text,
        }

    items = list(seen.values())[:limit]
    return ok(items)
