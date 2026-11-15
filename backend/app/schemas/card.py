"""Card Schema - 4 种卡片类型的 Pydantic 校验 + 统一接口"""
from datetime import datetime
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, field_validator

CardType = Literal["basic", "interview", "choice", "vocabulary"]


# ============================================================
# 4 种卡片的 front / back 结构定义（Pydantic 校验）
# ============================================================


# ---------- Basic ----------
class BasicFront(BaseModel):
    content: str = Field(..., min_length=1)


class BasicBack(BaseModel):
    content: str = Field(..., min_length=1)


# ---------- Interview ----------
class InterviewFront(BaseModel):
    question: str = Field(..., min_length=1)
    keywords: list[str] = Field(default_factory=list)


class InterviewBack(BaseModel):
    answer: str = Field(..., min_length=1)
    difficulty: int = Field(default=3, ge=1, le=5)


# ---------- Choice ----------
class ChoiceFront(BaseModel):
    question: str = Field(..., min_length=1)
    options: list[str] = Field(..., min_length=2)
    is_multiple: bool = False


class ChoiceBack(BaseModel):
    # correct_answer: 正确选项索引列表（0-based）
    correct_answer: list[int] = Field(..., min_length=1)
    explanation: str | None = None

    @field_validator("correct_answer")
    @classmethod
    def _check_indices(cls, v: list[int]) -> list[int]:
        if not all(0 <= i < 20 for i in v):
            raise ValueError("Option index out of range")
        return v


# ---------- Vocabulary ----------
class VocabularyFront(BaseModel):
    word: str = Field(..., min_length=1)
    phonetic: str | None = None
    audio_url: str | None = None


class VocabularyBack(BaseModel):
    cn_meaning: str | None = None
    en_meaning: str | None = None
    examples: list[str] = Field(default_factory=list)
    roots: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)

    @field_validator("cn_meaning", "en_meaning")
    @classmethod
    def _at_least_one_meaning(cls, v, info):
        # 允许任一为空，但调用方应至少填一个
        return v


# ============================================================
# 统一创建/更新请求
# ============================================================

FRONT_SCHEMAS: dict[str, type[BaseModel]] = {
    "basic": BasicFront,
    "interview": InterviewFront,
    "choice": ChoiceFront,
    "vocabulary": VocabularyFront,
}
BACK_SCHEMAS: dict[str, type[BaseModel]] = {
    "basic": BasicBack,
    "interview": InterviewBack,
    "choice": ChoiceBack,
    "vocabulary": VocabularyBack,
}


class CardCreateRequest(BaseModel):
    deck_id: int
    card_type: CardType
    front_content: dict[str, Any]
    back_content: dict[str, Any]
    explanation: str | None = None
    tag_ids: list[int] = Field(default_factory=list)

    @field_validator("front_content")
    @classmethod
    def _validate_front(cls, v: dict, info) -> dict:
        ctype = info.data.get("card_type")
        if ctype and ctype in FRONT_SCHEMAS:
            FRONT_SCHEMAS[ctype].model_validate(v)
        return v

    @field_validator("back_content")
    @classmethod
    def _validate_back(cls, v: dict, info) -> dict:
        ctype = info.data.get("card_type")
        if ctype and ctype in BACK_SCHEMAS:
            BACK_SCHEMAS[ctype].model_validate(v)
        return v


class CardUpdateRequest(BaseModel):
    card_type: CardType | None = None
    front_content: dict[str, Any] | None = None
    back_content: dict[str, Any] | None = None
    explanation: str | None = None
    tag_ids: list[int] | None = None


class CardResponse(BaseModel):
    id: int
    deck_id: int
    card_type: str
    front_content: dict[str, Any]
    back_content: dict[str, Any]
    explanation: str | None
    source_id: int | None
    created_at: datetime
    updated_at: datetime
    tags: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CardListResponse(BaseModel):
    items: list[CardResponse]
    total: int


class CardImportItem(BaseModel):
    card_type: CardType
    front_content: dict[str, Any]
    back_content: dict[str, Any]
    explanation: str | None = None


class CardImportRequest(BaseModel):
    deck_id: int
    cards: list[CardImportItem] = Field(..., min_length=1, max_length=500)
