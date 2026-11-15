"""联想记忆：卡片间关联"""
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class CardLink(Base):
    """卡片间的语义/结构关联

    relation_type:
      - prerequisite: A 是 B 的前置知识（先学 A 再学 B）
      - similar:       A 和 B 相似/容易混淆
      - contains:      A 包含 B（A 是上位概念）
      - contrast:      A 和 B 形成对比/对照
      - custom:        用户自定义
    """

    __tablename__ = "card_links"
    __table_args__ = (
        UniqueConstraint("card_id", "target_card_id", name="uq_card_link_pair"),
        Index("ix_card_links_target", "target_card_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="similar", index=True
    )
    note: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
