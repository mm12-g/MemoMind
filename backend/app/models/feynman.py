"""费曼学习法：解释会话 + 解释记录"""
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class FeynmanSession(Base):
    """一次费曼学习会话

    流程：选若干卡 → 轮流"用简单语言解释" → AI 评分（流畅度/简洁度/准确度）→
          卡壳标记 → 针对卡壳卡重试解释 → 会话总结
    """

    __tablename__ = "feynman_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deck_id: Mapped[int | None] = mapped_column(
        ForeignKey("decks.id", ondelete="SET NULL"), default=None
    )
    title: Mapped[str] = mapped_column(String(100), default="费曼学习")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True,
        comment="active/completed/abandoned",
    )
    card_count: Mapped[int] = mapped_column(default=0)
    explained_count: Mapped[int] = mapped_column(default=0)
    stuck_count: Mapped[int] = mapped_column(default=0)  # 被 AI 判定卡壳的卡数
    avg_clarity: Mapped[float | None] = mapped_column(default=None)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(default=None)


class FeynmanExplanation(Base):
    """单次解释尝试（会话内每张卡每次解释一行）"""

    __tablename__ = "feynman_explanations"
    __table_args__ = (Index("ix_feynman_exp_session", "session_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("feynman_sessions.id", ondelete="CASCADE"), nullable=False
    )
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt: Mapped[int] = mapped_column(default=1, comment="第几次解释")
    user_explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # AI 评分（0-10）
    clarity_score: Mapped[float | None] = mapped_column(default=None)      # 解释是否清晰（流畅度）
    simplicity_score: Mapped[float | None] = mapped_column(default=None)   # 是否用简单语言（专业术语暴露度）
    accuracy_score: Mapped[float | None] = mapped_column(default=None)     # 是否准确
    overall_score: Mapped[float | None] = mapped_column(default=None)

    is_stuck: Mapped[bool] = mapped_column(
        default=False, comment="AI 判定是否卡壳（overall < 6 即卡壳）"
    )
    stuck_spots: Mapped[list] = mapped_column(
        JSON, default=None, comment="卡壳点列表，如 ['忘了XX函数的返回值','混淆了XX和YY']"
    )
    suggestion: Mapped[str | None] = mapped_column(Text, default=None)
    ai_feedback: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
