"""测试共用 fixtures：内存 SQLite + TestClient"""
import os
import sys

# ===== 关键：在 import app 之前，用环境变量强制内存 SQLite =====
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# 让 `app` 包可被 import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

# 先手动建一个共享的 SQLite 内存 engine（StaticPool 保证所有 Session 用同一连接）
_shared_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)

# 覆盖 app 的 engine + SessionLocal，让 app 运行时全部走这个共享连接
import app.core.database as db_mod
db_mod.engine = _shared_engine
db_mod.SessionLocal = sessionmaker(bind=_shared_engine, autoflush=False, autocommit=False, future=True)

from app.core.database import Base, get_db
from app.main import app

# 用共享 engine 建表
Base.metadata.create_all(bind=_shared_engine)


@pytest.fixture()
def db_session():
    """每个测试一个新 session（但底层走同一个 StaticPool 连接）"""
    db = db_mod.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient，DI 覆盖成 test session"""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """注册 + 登录，拿到 Bearer token"""
    username = f"test_{os.getpid()}"
    email = f"{username}@test.com"
    client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": "TestPass123!",
    })
    # login 接口用 email + password
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "TestPass123!",
    })
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
