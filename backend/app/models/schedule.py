"""CardSchedule ORM - FSRS 卡片调度状态（1:1 关联 cards）"""
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class CardSchedule(Base):
    """FSRS 卡片调度状态

    与 Card 1:1 关联，存储 FSRS Card 对象的完整 JSON 序列化，
    同时冗余 state / due_at 用于快速查询到期卡片（免 JSONB 解析）。
    """

    __tablename__ = "card_schedules"

    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # FSRS Card.to_dict() 完整 JSON
    fsrs_card_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    # 冗余索引字段（从 fsrs_card_json 同步，保证查询性能）
    state: Mapped[int] = mapped_column(nullable=False, index=True)  # 1=Learning, 2=Review, 3=Relearning
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
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

    __table_args__ = (
        # 核心查询索引：查到期的学习/复习/重学卡片
        Index("ix_card_schedules_state_due", "state", "due_at"),
    )
