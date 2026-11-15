"""Deck Schema - 请求/响应"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["general", "interview", "exam", "vocabulary"]


class DeckCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    category: Category = "general"


class DeckUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: Category | None = None


class DeckResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    category: str
    card_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeckListResponse(BaseModel):
    items: list[DeckResponse]
    total: int
