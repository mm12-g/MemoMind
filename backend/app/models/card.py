"""Card ORM 模型 - 统一记忆卡片"""
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Card(Base):
    """统一记忆卡片

    卡片内容按类型存 JSONB：
    - Basic:         front={content},                      back={content}
    - Interview:     front={question, keywords},            back={answer, difficulty}
    - Choice:        front={question, options, is_multiple}, back={correct_answer, explanation}
    - Vocabulary:    front={word, phonetic, audio_url},     back={cn_meaning, en_meaning, examples, roots, synonyms, antonyms}
    """

    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deck_id: Mapped[int] = mapped_column(
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    card_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="basic/interview/choice/vocabulary",
    )
    front_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    back_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, default=None)
    source_id: Mapped[int | None] = mapped_column(default=None)  # P5 阶段关联 source_documents
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关系
    deck: Mapped["Deck"] = relationship(back_populates="cards")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="card_tags",
        back_populates="cards",
        cascade="save-update, merge",
    )
