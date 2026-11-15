"""Decks API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user
from ...core.exceptions import bad_request, conflict, not_found
from ...models.card import Card
from ...models.deck import Deck
from ...models.user import User
from ...schemas.common import ok
from ...schemas.deck import (
    DeckCreateRequest,
    DeckListResponse,
    DeckResponse,
    DeckUpdateRequest,
)

router = APIRouter(prefix="/decks")


def _enrich(deck: Deck, card_count: int | None = None) -> DeckResponse:
    """Deck → DeckResponse，附加 card_count"""
    return DeckResponse(
        id=deck.id,
        user_id=deck.user_id,
        name=deck.name,
        description=deck.description,
        category=deck.category,
        card_count=card_count if card_count is not None else 0,
        created_at=deck.created_at,
        updated_at=deck.updated_at,
    )


@router.post("")
def create_deck(
    req: DeckCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deck = Deck(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        category=req.category,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return ok(_enrich(deck))


@router.get("")
def list_decks(
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Deck).filter(Deck.user_id == current_user.id)
    if category:
        q = q.filter(Deck.category == category)
    if keyword:
        q = q.filter(Deck.name.ilike(f"%{keyword}%"))
    decks = q.order_by(Deck.updated_at.desc()).all()

    # 一次查出每个 Deck 的 card_count
    counts = dict(
        db.query(Card.deck_id, func.count(Card.id))
        .filter(Card.deck_id.in_([d.id for d in decks]))
        .group_by(Card.deck_id)
        .all()
    )

    items = [_enrich(d, counts.get(d.id, 0)) for d in decks]
    return ok(DeckListResponse(items=items, total=len(items)))


@router.get("/{deck_id}")
def get_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deck = (
        db.query(Deck)
        .filter(Deck.id == deck_id, Deck.user_id == current_user.id)
        .first()
    )
    if not deck:
        raise not_found("Deck")
    count = db.query(func.count(Card.id)).filter(Card.deck_id == deck.id).scalar() or 0
    return ok(_enrich(deck, count))


@router.put("/{deck_id}")
def update_deck(
    deck_id: int,
    req: DeckUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deck = (
        db.query(Deck)
        .filter(Deck.id == deck_id, Deck.user_id == current_user.id)
        .first()
    )
    if not deck:
        raise not_found("Deck")

    for k, v in req.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(deck, k, v)

    db.commit()
    db.refresh(deck)
    count = db.query(func.count(Card.id)).filter(Card.deck_id == deck.id).scalar() or 0
    return ok(_enrich(deck, count))


@router.delete("/{deck_id}")
def delete_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deck = (
        db.query(Deck)
        .filter(Deck.id == deck_id, Deck.user_id == current_user.id)
        .first()
    )
    if not deck:
        raise not_found("Deck")

    db.delete(deck)
    db.commit()
    return ok({"deleted": deck_id})
