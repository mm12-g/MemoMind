"""Review Schema"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RatingInt = Literal[1, 2, 3, 4]


class ReviewSubmitRequest(BaseModel):
    session_id: int | None = None
    rating: RatingInt  # 1=Again, 2=Hard, 3=Good, 4=Easy
    response_time_ms: int | None = None
    answer_text: str | None = None
    idempotency_key: str | None = None  # 客户端生成，防止重复提交


class ReviewSubmitResponse(BaseModel):
    card_id: int
    new_state: int
    new_state_label: str
    next_due_at: datetime
    scheduled_days: int | None
    elapsed_days: int | None


class ReviewStartRequest(BaseModel):
    deck_id: int | None = None
    session_token: str | None = None


class ReviewStartResponse(BaseModel):
    session_id: int
    cards: list[dict]


class ReviewHistoryParams(BaseModel):
    card_id: int | None = None
    start_date: str | None = None  # YYYY-MM-DD
    end_date: str | None = None
    page: int = 1
    page_size: int = 20
