"""分析与统计服务测试"""
import pytest
from datetime import datetime, timezone, timedelta


def test_dashboard_stats_empty_user(client, auth_headers):
    """新用户没有任何复习记录，统计应该返回 0 而不是报错"""
    r = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["due_today"] >= 0
    assert data["streak_days"] >= 0


def test_review_statistics_empty_user(client, auth_headers):
    r = client.get("/api/v1/reviews/statistics", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["total_reviews"] == 0


def test_retention_empty_user(client, auth_headers):
    r = client.get("/api/v1/analytics/retention", headers=auth_headers)
    assert r.status_code == 200, r.text


def test_mistakes_empty_user(client, auth_headers):
    r = client.get("/api/v1/practice/mistakes", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"] == []


def test_goals_daily_empty_user(client, auth_headers):
    r = client.get("/api/v1/goals/daily", headers=auth_headers)
    assert r.status_code == 200


def test_batch_delete_bulk(client, auth_headers):
    """批量删除卡片"""
    # 先建 deck
    r = client.post("/api/v1/decks", json={"name": "Batch", "description": ""}, headers=auth_headers)
    assert r.status_code == 200, r.text
    deck_data = r.json()["data"]
    deck_id = deck_data["id"] if isinstance(deck_data, dict) else deck_data[0]["id"]

    # 建 3 张卡
    ids = []
    for i in range(3):
        r = client.post("/api/v1/cards", json={
            "deck_id": deck_id,
            "card_type": "basic",
            "front_content": {"content": f"Q{i}"},
            "back_content": {"content": f"A{i}"},
        }, headers=auth_headers)
        assert r.status_code == 200, r.text
        card_data = r.json()["data"]
        card_id = card_data["id"] if isinstance(card_data, dict) else card_data[0]["id"]
        ids.append(card_id)

    # 单张删除（DELETE /cards/{id}）
    r2 = client.delete(f"/api/v1/cards/{ids[0]}", headers=auth_headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["deleted"] == ids[0]

    # 剩 2 张
    r3 = client.get(f"/api/v1/cards?deck_id={deck_id}", headers=auth_headers)
    total = r3.json()["data"].get("total", 0)
    assert total == 2
