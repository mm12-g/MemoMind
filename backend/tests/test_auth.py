"""Auth API 测试"""
import pytest


def test_register_then_login(client):
    username = "auth_test_user"
    email = "auth_test@test.com"

    r = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": "TestPass123!",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["code"] == 0
    assert data["data"]["username"] == username

    r2 = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "TestPass123!",
    })
    assert r2.status_code == 200
    token = r2.json()["data"]["access_token"]
    assert token, "应该返回 access_token"


def test_duplicate_email_register_fails(client):
    client.post("/api/v1/auth/register", json={
        "username": "u1", "email": "dup@dup.com", "password": "TestPass1!",
    })
    r = client.post("/api/v1/auth/register", json={
        "username": "u2", "email": "dup@dup.com", "password": "TestPass2!",
    })
    # 重复邮箱应该被拒绝
    assert r.status_code in (400, 409), r.text


def test_wrong_login_password_fails(client):
    client.post("/api/v1/auth/register", json={
        "username": "wrong_pw", "email": "w@w.com", "password": "TestPass1!",
    })
    r = client.post("/api/v1/auth/login", json={
        "email": "w@w.com", "password": "WRONG_PASS!",
    })
    assert r.status_code == 401, r.text


def test_protected_endpoint_rejects_no_token(client):
    r = client.get("/api/v1/decks")
    assert r.status_code in (401, 403)


def test_protected_endpoint_accepts_token(client, auth_headers):
    r = client.get("/api/v1/decks", headers=auth_headers)
    assert r.status_code == 200
