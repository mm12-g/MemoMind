"""费曼学习法 Service + API"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.prompts import (
    SYSTEM_FEYNMAN_EVAL,
    USER_FEYNMAN_TEMPLATE,
)
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.card import Card
from app.models.deck import Deck
from app.models.feynman import FeynmanExplanation, FeynmanSession
from app.models.user import User
from app.schemas.common import ok
from app.services.ai_service import call_ai_json

router = APIRouter(prefix="/feynman", tags=["feynman"])


# ---------- Schemas ----------
class FeynmanStart(BaseModel):
    deck_id: int | None = None
    card_ids: list[int] | None = None  # 指定卡片优先于 deck_id
    count: int = 8
    title: str | None = None


class FeynmanExplain(BaseModel):
    card_id: int
    user_explanation: str


class FeynmanComplete(BaseModel):
    status: str = "completed"  # completed / abandoned


class FeynmanExplainOut(BaseModel):
    id: int
    card_id: int
    card_preview: str
    attempt: int
    user_explanation: str
    clarity_score: float | None
    simplicity_score: float | None
    accuracy_score: float | None
    overall_score: float | None
    is_stuck: bool
    stuck_spots: list | None
    suggestion: str | None
    ai_feedback: str | None


# ---------- Helpers ----------
def _card_preview(card: Card) -> str:
    if card.card_type == "basic":
        return card.front_content.get("content", "")
    if card.card_type == "interview":
        return card.front_content.get("question", "")
    if card.card_type == "choice":
        return card.front_content.get("question", "")
    if card.card_type == "vocabulary":
        return card.front_content.get("word", "")
    return ""


def _concept_full(card: Card) -> str:
    """把卡片变成一段可以被解释的"知识"文本"""
    parts = [f"卡片类型：{card.card_type}"]
    parts.append(f"内容：{_card_preview(card)}")
    if card.back_content:
        back_text = json.dumps(card.back_content, ensure_ascii=False)
        parts.append(f"参考答案：{back_text}")
    if card.explanation:
        parts.append(f"补充说明：{card.explanation}")
    return "\n".join(parts)


def _evaluate_feynman(concept: str, explanation: str) -> dict:
    """调用 AI 给一次解释评分"""
    user_prompt = USER_FEYNMAN_TEMPLATE.format(concept=concept, explanation=explanation)
    try:
        result = call_ai_json(SYSTEM_FEYNMAN_EVAL, user_prompt, timeout=30)
        # 容错：AI 可能漏掉 overall
        if "overall" not in result or result.get("overall") is None:
            c = result.get("clarity", 5)
            s = result.get("simplicity", 5)
            a = result.get("accuracy", 5)
            result["overall"] = round((c + s + a) / 3, 1)
        if "is_stuck" not in result:
            result["is_stuck"] = result.get("overall", 10) < 6
        if "stuck_spots" not in result:
            result["stuck_spots"] = []
        return result
    except Exception as e:
        # AI 不可用时给一个中性结果
        return {
            "clarity": 5.0, "simplicity": 5.0, "accuracy": 5.0,
            "overall": 5.0, "is_stuck": False,
            "stuck_spots": [],
            "suggestion": "AI 暂时不可用，手动判断一下卡壳了吗？",
            "ai_feedback": f"AI 未回复（{e}），请稍后重试以获得更准确的评估。",
        }


# ---------- APIs ----------
@router.post("/sessions")
def start_session(
    body: FeynmanStart,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建费曼学习会话"""
    card_ids = body.card_ids

    if card_ids:
        cards = db.query(Card).filter(Card.id.in_(card_ids), Card.deck.has(user_id=user.id)).all()
    elif body.deck_id:
        deck = db.query(Deck).filter(Deck.id == body.deck_id, Deck.user_id == user.id).first()
        if not deck:
            raise HTTPException(status_code=404, detail="知识库不存在")
        cards = (
            db.query(Card)
            .filter(Card.deck_id == deck.id)
            .order_by(func.random())
            .limit(body.count)
            .all()
        )
    else:
        # 全用户随机取
        cards = (
            db.query(Card)
            .filter(Card.deck.has(user_id=user.id))
            .order_by(func.random())
            .limit(body.count)
            .all()
        )

    if not cards:
        raise HTTPException(status_code=400, detail="没有卡片可以学习")

    title = body.title or f"费曼 · {len(cards)} 张卡"
    session = FeynmanSession(
        user_id=user.id,
        deck_id=body.deck_id,
        title=title,
        status="active",
        card_count=len(cards),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 返回会话 + 卡片列表（不存 card_ids，直接返回给前端持有）
    return ok({
        "session_id": session.id,
        "title": session.title,
        "card_count": len(cards),
        "cards": [
            {
                "card_id": c.id,
                "card_type": c.card_type,
                "preview": _card_preview(c),
                "concept": _concept_full(c),
            }
            for c in cards
        ],
    })


@router.post("/sessions/{session_id}/explain")
def submit_explanation(
    session_id: int,
    body: FeynmanExplain,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交一次解释，AI 评分"""
    session = (
        db.query(FeynmanSession)
        .filter(FeynmanSession.id == session_id, FeynmanSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    card_id = body.card_id

    card = (
        db.query(Card)
        .filter(Card.id == card_id, Card.deck.has(user_id=user.id))
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")

    # 当前卡已经解释过几次
    existing_count = (
        db.query(func.count(FeynmanExplanation.id))
        .filter(
            FeynmanExplanation.session_id == session_id,
            FeynmanExplanation.card_id == card_id,
        )
        .scalar()
    )
    attempt = existing_count + 1

    eval_result = _evaluate_feynman(_concept_full(card), body.user_explanation)

    explanation = FeynmanExplanation(
        session_id=session.id,
        card_id=card.id,
        attempt=attempt,
        user_explanation=body.user_explanation,
        clarity_score=eval_result.get("clarity"),
        simplicity_score=eval_result.get("simplicity"),
        accuracy_score=eval_result.get("accuracy"),
        overall_score=eval_result.get("overall"),
        is_stuck=eval_result.get("is_stuck", False),
        stuck_spots=eval_result.get("stuck_spots"),
        suggestion=eval_result.get("suggestion"),
        ai_feedback=eval_result.get("ai_feedback"),
    )
    db.add(explanation)

    # 更新 session 统计
    session.explained_count = (session.explained_count or 0) + 1
    if eval_result.get("is_stuck"):
        session.stuck_count = (session.stuck_count or 0) + 1

    db.commit()
    db.refresh(explanation)

    return ok(FeynmanExplainOut(
        id=explanation.id,
        card_id=card_id,
        card_preview=_card_preview(card),
        attempt=attempt,
        user_explanation=body.user_explanation,
        clarity_score=explanation.clarity_score,
        simplicity_score=explanation.simplicity_score,
        accuracy_score=explanation.accuracy_score,
        overall_score=explanation.overall_score,
        is_stuck=explanation.is_stuck,
        stuck_spots=explanation.stuck_spots,
        suggestion=explanation.suggestion,
        ai_feedback=explanation.ai_feedback,
    ).model_dump())


@router.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: int,
    body: FeynmanComplete,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = (
        db.query(FeynmanSession)
        .filter(FeynmanSession.id == session_id, FeynmanSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    session.status = body.status
    session.ended_at = datetime.now(timezone.utc)

    # 计算平均分
    scores = (
        db.query(FeynmanExplanation.overall_score)
        .filter(FeynmanExplanation.session_id == session_id)
        .all()
    )
    valid = [s[0] for s in scores if s[0] is not None]
    if valid:
        session.avg_clarity = round(sum(valid) / len(valid), 2)

    db.commit()
    return ok({
        "session_id": session.id,
        "status": session.status,
        "explained_count": session.explained_count,
        "stuck_count": session.stuck_count,
        "avg_clarity": session.avg_clarity,
        "duration_seconds": int(
            (session.ended_at.replace(tzinfo=None) - session.started_at.replace(tzinfo=None)).total_seconds()
        ),
    })


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sessions = (
        db.query(FeynmanSession)
        .filter(FeynmanSession.user_id == user.id)
        .order_by(FeynmanSession.started_at.desc())
        .limit(20)
        .all()
    )
    return ok([
        {
            "id": s.id,
            "title": s.title,
            "status": s.status,
            "card_count": s.card_count,
            "explained_count": s.explained_count,
            "stuck_count": s.stuck_count,
            "avg_clarity": s.avg_clarity,
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        }
        for s in sessions
    ])
