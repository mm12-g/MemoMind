"""FSRS 复习流程测试"""
import pytest
from datetime import datetime, timezone, timedelta


def _create_deck_and_card(client, auth_headers):
    r = client.post("/api/v1/decks", json={
        "name": "Test Deck", "description": "desc",
    }, headers=auth_headers)
    assert r.status_code == 200, r.text
    deck_data = r.json()["data"]
    deck_id = deck_data["id"] if isinstance(deck_data, dict) else deck_data[0]["id"]

    r = client.post("/api/v1/cards", json={
        "deck_id": deck_id,
        "card_type": "basic",
        "front_content": {"content": "What is 2+2?"},
        "back_content": {"content": "4"},
    }, headers=auth_headers)
    assert r.status_code == 200, r.text
    card_data = r.json()["data"]
    card_id = card_data["id"] if isinstance(card_data, dict) else card_data[0]["id"]
    return deck_id, card_id


def test_create_card_has_schedule(client, auth_headers):
    deck_id, card_id = _create_deck_and_card(client, auth_headers)

    r = client.get(f"/api/v1/cards/{card_id}", headers=auth_headers)
    assert r.status_code == 200


def test_start_session_returns_cards(client, auth_headers):
    _create_deck_and_card(client, auth_headers)

    # 强制把卡片设为到期（due_at 是今天）
    from app.core.database import SessionLocal
    from app.models.schedule import CardSchedule
    import app.models.card as card_mod

    db = SessionLocal()
    c = db.query(card_mod.Card).first()
    if c:
        s = db.query(CardSchedule).filter(CardSchedule.card_id == c.id).first()
        if s:
            s.due_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
    db.close()

    r = client.post("/api/v1/reviews/start", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert "session_id" in data
    assert isinstance(data["cards"], list)


def test_submit_rating_updates_schedule(client, auth_headers):
    deck_id, card_id = _create_deck_and_card(client, auth_headers)

    # 先开始
    start = client.post("/api/v1/reviews/start", headers=auth_headers)
    session_id = start.json()["data"]["session_id"]

    # 把卡片置顶
    start2 = client.post(f"/api/v1/reviews/start?card_id={card_id}", headers=auth_headers)
    session_id = start2.json()["data"]["session_id"]

    first = start2.json()["data"]["cards"][0]
    assert first["card_id"] == card_id

    # 提交 Good（rating=3）— submit 路径是 /reviews/submit/{card_id}
    r = client.post(f"/api/v1/reviews/submit/{card_id}", json={
        "session_id": session_id,
        "rating": 3,
        "time_ms": 5000,
    }, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    # submit 返回 ReviewSubmitResponse：{card_id, new_state, next_due_at, ...}
    assert data["card_id"] == card_id
    assert "next_due_at" in data
