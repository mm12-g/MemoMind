"""ReviewLog ORM - 复习日志"""
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Integer, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ReviewLog(Base):
    """复习日志 - 每次复习提交写一条"""

    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="SET NULL"), default=None
    )
    rating: Mapped[int] = mapped_column(nullable=False, comment="1=Again, 2=Hard, 3=Good, 4=Easy")
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    elapsed_days: Mapped[int | None] = mapped_column(default=None, comment="实际间隔天数")
    scheduled_days: Mapped[int | None] = mapped_column(default=None, comment="计划间隔天数")
    response_time_ms: Mapped[int | None] = mapped_column(default=None, comment="回答耗时")
    answer_text: Mapped[str | None] = mapped_column(default=None)
    ai_score: Mapped[dict | None] = mapped_column(JSON, default=None)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), default=True, unique=True)

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_review_logs_idempotency"),
        Index("ix_review_logs_user_reviewed", "user_id", "reviewed_at"),
        Index("ix_review_logs_card", "card_id"),
    )
