"""StudySession / LearningGoal ORM"""
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class StudySession(Base):
    """一次学习会话（用户点开始复习 → 退出/结束）"""

    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    reviewed_count: Mapped[int] = mapped_column(default=0)
    new_count: Mapped[int] = mapped_column(default=0)
    duration_seconds: Mapped[int | None] = mapped_column(default=None)


class LearningGoal(Base):
    """学习目标 - 每个用户一套"""

    __tablename__ = "learning_goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False, unique=True, index=True)
    daily_new_limit: Mapped[int] = mapped_column(default=20)
    daily_review_limit: Mapped[int] = mapped_column(default=200)
    daily_minutes_goal: Mapped[int] = mapped_column(default=30)
    desired_retention: Mapped[float] = mapped_column(default=0.9)
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
