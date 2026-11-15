"""Tag Schema"""
from datetime import datetime

from pydantic import BaseModel, Field


class TagCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str | None = None


class TagUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = None


class TagResponse(BaseModel):
    id: int
    user_id: int
    name: str
    color: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
