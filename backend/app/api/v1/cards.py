"""Cards API"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, Text, cast
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user
from ...core.exceptions import bad_request, not_found, forbidden
from ...models.card import Card
from ...models.deck import Deck
from ...models.schedule import CardSchedule
from ...models.tag import Tag
from ...models.user import User
from ...schemas.card import (
    CardCreateRequest,
    CardImportRequest,
    CardListResponse,
    CardResponse,
    CardUpdateRequest,
)
from ...schemas.common import ok
from ...services.fsrs_service import card_to_json, new_card

router = APIRouter(prefix="/cards")


def _to_response(card: Card) -> CardResponse:
    return CardResponse(
        id=card.id,
        deck_id=card.deck_id,
        card_type=card.card_type,
        front_content=card.front_content,
        back_content=card.back_content,
        explanation=card.explanation,
        source_id=card.source_id,
        created_at=card.created_at,
        updated_at=card.updated_at,
        tags=[{"id": t.id, "name": t.name, "color": t.color} for t in card.tags],
    )


def _ensure_deck_owner(deck: Deck, current_user: User) -> None:
    if deck.user_id != current_user.id:
        raise forbidden("Deck not owned by current user")


def _init_schedule_for_new_card(db: Session, card_id: int) -> CardSchedule:
    """为新卡片初始化 FSRS CardSchedule（state=Learning, due=now）"""
    fsrs_card = new_card()
    now = datetime.now(timezone.utc)
    schedule = CardSchedule(
        card_id=card_id,
        fsrs_card_json=card_to_json(fsrs_card),
        state=fsrs_card.state,
        due_at=now,
        last_review_at=None,
    )
    db.add(schedule)
    return schedule


@router.post("")
def create_card(
    req: CardCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deck = db.query(Deck).filter(Deck.id == req.deck_id).first()
    if not deck:
        raise not_found("Deck")
    _ensure_deck_owner(deck, current_user)

    card = Card(
        deck_id=deck.id,
        card_type=req.card_type,
        front_content=req.front_content,
        back_content=req.back_content,
        explanation=req.explanation,
    )
    db.add(card)
    db.flush()  # 拿到 card.id

    # 自动创建 FSRS 调度状态
    _init_schedule_for_new_card(db, card.id)

    # 处理标签
    if req.tag_ids:
        tags = (
            db.query(Tag)
            .filter(Tag.id.in_(req.tag_ids), Tag.user_id == current_user.id)
            .all()
        )
        card.tags = tags

    db.commit()
    db.refresh(card)
    return ok(_to_response(card))


@router.get("")
def list_cards(
    deck_id: int | None = Query(default=None),
    card_type: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    tag_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Card).join(Deck, Deck.id == Card.deck_id).filter(
        Deck.user_id == current_user.id
    )

    if deck_id:
        q = q.filter(Card.deck_id == deck_id)
    if card_type:
        q = q.filter(Card.card_type == card_type)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            or_(
                cast(Card.front_content, Text).ilike(kw),
                cast(Card.back_content, Text).ilike(kw),
                Card.explanation.ilike(kw),
            )
        )
    if tag_id:
        q = q.filter(Card.tags.any(Tag.id == tag_id))

    total = q.count()
    items = q.order_by(Card.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return ok(
        {
            "items": [_to_response(c) for c in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/{card_id}")
def get_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    card = (
        db.query(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id == card_id, Deck.user_id == current_user.id)
        .first()
    )
    if not card:
        raise not_found("Card")
    return ok(_to_response(card))


@router.put("/{card_id}")
def update_card(
    card_id: int,
    req: CardUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    card = (
        db.query(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id == card_id, Deck.user_id == current_user.id)
        .first()
    )
    if not card:
        raise not_found("Card")

    data = req.model_dump(exclude_unset=True, exclude_none=True)
    tag_ids = data.pop("tag_ids", None)

    for k, v in data.items():
        setattr(card, k, v)

    if tag_ids is not None:
        tags = (
            db.query(Tag)
            .filter(Tag.id.in_(tag_ids), Tag.user_id == current_user.id)
            .all()
        )
        card.tags = tags

    db.commit()
    db.refresh(card)
    return ok(_to_response(card))


@router.delete("/{card_id}")
def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    card = (
        db.query(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id == card_id, Deck.user_id == current_user.id)
        .first()
    )
    if not card:
        raise not_found("Card")

    db.delete(card)
    db.commit()
    return ok({"deleted": card_id})


@router.delete("/batch")
def batch_delete(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除卡片：{ card_ids: [1, 2, 3] }"""
    ids = body.get("card_ids", [])
    if not ids:
        return ok({"deleted": 0})

    cards = (
        db.query(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .filter(Card.id.in_(ids), Deck.user_id == current_user.id)
        .all()
    )
    count = len(cards)
    for c in cards:
        db.delete(c)
    db.commit()
    return ok({"deleted": count})


@router.post("/import")
def import_cards(
    req: CardImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量导入卡片（JSON 格式）- 自动初始化 FSRS 状态"""
    deck = db.query(Deck).filter(Deck.id == req.deck_id).first()
    if not deck:
        raise not_found("Deck")
    _ensure_deck_owner(deck, current_user)

    created = 0
    for item in req.cards:
        card = Card(
            deck_id=deck.id,
            card_type=item.card_type,
            front_content=item.front_content,
            back_content=item.back_content,
            explanation=item.explanation,
        )
        db.add(card)
        db.flush()
        _init_schedule_for_new_card(db, card.id)
        created += 1

    db.commit()
    return ok({"created": created})
