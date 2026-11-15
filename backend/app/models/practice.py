"""ExamRecord / InterviewSession / VocabSession ORM - 专项训练记录"""
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Integer, JSON, Float, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ExamRecord(Base):
    """模拟考试记录"""

    __tablename__ = "exam_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    deck_id: Mapped[int | None] = mapped_column(default=None)
    card_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, comment="本次考试抽取的 card_id 列表")
    answers: Mapped[list[dict]] = mapped_column(JSON, default=list, comment="用户作答 [{card_id, answer, correct}]")
    total_count: Mapped[int] = mapped_column(nullable=False)
    correct_count: Mapped[int] = mapped_column(default=0)
    score: Mapped[float] = mapped_column(default=0.0, comment="百分制")
    duration_seconds: Mapped[int | None] = mapped_column(default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class InterviewSession(Base):
    """面试专项训练记录"""

    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    deck_id: Mapped[int | None] = mapped_column(default=None)
    card_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    scores: Mapped[list[dict]] = mapped_column(JSON, default=list, comment="AI 评分结果")
    avg_score: Mapped[float] = mapped_column(default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
