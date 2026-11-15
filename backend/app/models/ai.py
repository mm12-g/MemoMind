"""SourceDocument / AiTask / AiGeneration ORM"""
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class SourceDocument(Base):
    """上传的知识源文档"""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="pdf/docx/txt/md")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text, default=None, comment="解析后的纯文本")
    status: Mapped[str] = mapped_column(String(20), default="uploaded", comment="uploaded/parsed/failed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AiTask(Base):
    """AI 任务（异步处理用）"""

    __tablename__ = "ai_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="document_parse/card_generate/answer_evaluate/question_generate",
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/processing/completed/failed")
    progress: Mapped[int] = mapped_column(default=0, comment="0-100")
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    # 关联资源（可空）
    deck_id: Mapped[int | None] = mapped_column(default=None)
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL"), default=None
    )
    # 输入参数快照
    input_payload: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class AiGeneration(Base):
    """AI 生成的卡片 / 评分结果"""

    __tablename__ = "ai_generations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("ai_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # AI 原始输出（卡片 JSON / 评分结果）
    output: Mapped[dict] = mapped_column(JSON, nullable=False)
    generation_type: Mapped[str] = mapped_column(
        String(50),
        default="card",
        comment="card/answer_eval/question",
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/approved/rejected")
    # 如果审核通过 → 关联正式卡片
    saved_card_id: Mapped[int | None] = mapped_column(default=None)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
