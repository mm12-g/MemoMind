"""联想记忆 Service + API"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.card import Card
from app.models.card_link import CardLink
from app.models.user import User
from app.schemas.common import ok

router = APIRouter(prefix="/links", tags=["associate"])

RELATION_TYPES = ["prerequisite", "similar", "contains", "contrast", "custom"]
RELATION_LABEL = {
    "prerequisite": "前置知识",
    "similar": "相似",
    "contains": "包含",
    "contrast": "对比",
    "custom": "自定义",
}


# ---------- Schemas ----------
class CardLinkCreate(BaseModel):
    target_card_id: int
    relation_type: str = "similar"
    note: str | None = None


class CardLinkOut(BaseModel):
    id: int
    card_id: int
    target_card_id: int
    relation_type: str
    relation_label: str
    note: str | None
    target_card_preview: str  # 目标卡的简短预览

    class Config:
        from_attributes = True


class CardSuggestion(BaseModel):
    title: str
    reason: str
    suggested_card_type: str


# ---------- Helpers ----------
def _card_preview(card: Card) -> str:
    """生成简短预览"""
    if card.card_type == "basic":
        return card.front_content.get("content", "")
    if card.card_type == "interview":
        return card.front_content.get("question", "")
    if card.card_type == "choice":
        return card.front_content.get("question", "")
    if card.card_type == "vocabulary":
        return card.front_content.get("word", "")
    return ""


def _get_or_404(db: Session, card_id: int, user: User) -> Card:
    card = db.query(Card).filter(Card.id == card_id, Card.deck.has(user_id=user.id)).first()
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return card


# ---------- APIs ----------
@router.post("")
def create_link(
    card_id: int,
    body: CardLinkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """给 card_id 添加一个关联目标"""
    if body.relation_type not in RELATION_TYPES:
        raise HTTPException(status_code=400, detail=f"relation_type 必须是 {RELATION_TYPES}")

    _get_or_404(db, card_id, user)
    target = _get_or_404(db, body.target_card_id, user)
    if card_id == body.target_card_id:
        raise HTTPException(status_code=400, detail="不能关联自己")

    # 避免重复
    existing = (
        db.query(CardLink)
        .filter(CardLink.card_id == card_id, CardLink.target_card_id == body.target_card_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="已存在此关联")

    link = CardLink(
        card_id=card_id,
        target_card_id=body.target_card_id,
        relation_type=body.relation_type,
        note=body.note,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return ok(_serialize(link, target).model_dump())


@router.delete("/{link_id}")
def delete_link(
    card_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    link = (
        db.query(CardLink)
        .join(Card, Card.id == CardLink.card_id)
        .filter(CardLink.id == link_id, Card.id == card_id, Card.deck.has(user_id=user.id))
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="关联不存在")
    db.delete(link)
    db.commit()
    return ok({"deleted": link_id})


@router.get("")
def list_links(
    card_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出一张卡的所有关联（双向）"""
    _get_or_404(db, card_id, user)

    # 正向关联（card 是 A）
    forward = (
        db.query(CardLink)
        .filter(CardLink.card_id == card_id)
        .all()
    )
    # 反向关联（card 是 B，目标指向我）
    backward = (
        db.query(CardLink)
        .filter(CardLink.target_card_id == card_id)
        .all()
    )

    result: list[dict] = []
    for link in forward:
        target = db.query(Card).filter(Card.id == link.target_card_id).first()
        if target:
            result.append(_serialize(link, target).model_dump())
    for link in backward:
        src = db.query(Card).filter(Card.id == link.card_id).first()
        if src:
            result.append(_serialize_reverse(link, src).model_dump())
    return ok(result)


def _serialize(link: CardLink, target: Card) -> CardLinkOut:
    return CardLinkOut(
        id=link.id,
        card_id=link.card_id,
        target_card_id=link.target_card_id,
        relation_type=link.relation_type,
        relation_label=RELATION_LABEL.get(link.relation_type, link.relation_type),
        note=link.note,
        target_card_preview=_card_preview(target),
    )


def _serialize_reverse(link: CardLink, source: Card) -> CardLinkOut:
    # 反向关联：把 source 显示为"关联的对方"
    return CardLinkOut(
        id=link.id,
        card_id=link.target_card_id,  # 把当前 card 放 card_id 位置
        target_card_id=link.card_id,
        relation_type=link.relation_type + "_of",  # 标记是反向
        relation_label=f"{RELATION_LABEL.get(link.relation_type, link.relation_type)}（被关联）",
        note=link.note,
        target_card_preview=_card_preview(source),
    )
