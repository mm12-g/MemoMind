"""Tags API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user
from ...core.exceptions import not_found
from ...models.card import Card
from ...models.deck import Deck
from ...models.tag import Tag, card_tags
from ...models.user import User
from ...schemas.common import ok
from ...schemas.tag import TagCreateRequest, TagResponse, TagUpdateRequest

router = APIRouter(prefix="/tags")


def _to_response(tag: Tag, card_count: int = 0) -> TagResponse | dict:
    return {
        "id": tag.id,
        "user_id": tag.user_id,
        "name": tag.name,
        "color": tag.color,
        "created_at": tag.created_at,
        "card_count": card_count,
    }


@router.post("")
def create_tag(
    req: TagCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = Tag(user_id=current_user.id, name=req.name, color=req.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return ok(_to_response(tag))


@router.get("")
def list_tags(
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Tag).filter(Tag.user_id == current_user.id)
    if keyword:
        q = q.filter(Tag.name.ilike(f"%{keyword}%"))
    tags = q.order_by(Tag.name).all()

    # 统计每个 tag 下 card 数量（只统计自己的 cards）
    counts_sub = (
        db.query(
            Tag.id.label("tag_id"),
            func.count(Card.id).label("cnt"),
        )
        .join(card_tags, card_tags.c.tag_id == Tag.id)
        .join(Card, Card.id == card_tags.c.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Deck.user_id == current_user.id)
        .group_by(Tag.id)
        .subquery()
    )
    counts = dict(
        db.query(counts_sub.c.tag_id, counts_sub.c.cnt).all()
    )

    return ok([_to_response(t, counts.get(t.id, 0)) for t in tags])


@router.put("/{tag_id}")
def update_tag(
    tag_id: int,
    req: TagUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise not_found("Tag")

    for k, v in req.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(tag, k, v)

    db.commit()
    db.refresh(tag)
    return ok(_to_response(tag))


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise not_found("Tag")

    db.delete(tag)
    db.commit()
    return ok({"deleted": tag_id})


@router.post("/{tag_id}/cards/{card_id}")
def attach_tag_to_card(
    tag_id: int,
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    card = (
        db.query(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id == card_id, Deck.user_id == current_user.id)
        .first()
    )
    if not tag or not card:
        raise not_found("Tag or Card")

    if tag not in card.tags:
        card.tags.append(tag)
        db.commit()

    return ok({"attached": True})


@router.delete("/{tag_id}/cards/{card_id}")
def detach_tag_from_card(
    tag_id: int,
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    card = (
        db.query(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id == card_id, Deck.user_id == current_user.id)
        .first()
    )
    if not tag or not card:
        raise not_found("Tag or Card")

    if tag in card.tags:
        card.tags.remove(tag)
        db.commit()

    return ok({"detached": True})
