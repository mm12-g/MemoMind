"""AI API - 文档上传 / 卡片生成 / 评分 / 出题 / 审核"""
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from ...core.database import get_db, SessionLocal  # SessionLocal 用于后台线程
from ...core.deps import get_current_user
from ...core.exceptions import bad_request, not_found, forbidden
from ...core.config import settings
from ...models.ai import SourceDocument, AiTask, AiGeneration
from ...models.card import Card
from ...models.deck import Deck
from ...models.schedule import CardSchedule
from ...models.user import User
from ...schemas.card import CardCreateRequest
from ...schemas.common import ok
from ...services.document_parser import parse_file, validate_file
from ...services.ai_service import (
    evaluate_answer,
    generate_cards_from_text,
    generate_questions,
)
from ...services.fsrs_service import card_to_json, new_card

router = APIRouter(prefix="/ai")

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


def _background_task(func, *args, **kwargs):
    """在后台线程执行"""
    t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    t.start()


def _get_task_and_doc(db2: SessionLocal, task_id: int, doc_id: int | None = None):
    """后台线程专用：从 db2 查 task 和 doc（避免跨 session ORM 对象）"""
    task = db2.query(AiTask).filter(AiTask.id == task_id).first()
    doc = db2.query(SourceDocument).filter(SourceDocument.id == doc_id).first() if doc_id else None
    return task, doc


def _save_generations(db2: SessionLocal, task_id: int, cards: list[dict]) -> int:
    """写入 ai_generations"""
    for c in cards:
        gen = AiGeneration(
            task_id=task_id,
            output=c,
            generation_type="card",
            status="pending",
        )
        db2.add(gen)
    db2.commit()
    return len(cards)


def _approve_generation(db: Session, gen_id: int, current_user: User) -> Card | None:
    """审核通过 → 写入正式 cards + card_schedules"""
    gen = db.query(AiGeneration).filter(AiGeneration.id == gen_id).first()
    if not gen:
        return None
    if gen.status == "approved":
        return gen.saved_card_id

    task = db.query(AiTask).filter(AiTask.id == gen.task_id).first()
    if not task or not task.deck_id:
        raise bad_request("Task 没有关联知识库")

    deck = db.query(Deck).filter(
        Deck.id == task.deck_id, Deck.user_id == current_user.id
    ).first()
    if not deck:
        raise not_found("Deck")

    data = gen.output
    try:
        card = Card(
            deck_id=deck.id,
            card_type=data["card_type"],
            front_content=data["front_content"],
            back_content=data["back_content"],
            explanation=data.get("explanation"),
        )
        db.add(card)
        db.flush()

        fsrs_card = new_card()
        now = datetime.now(timezone.utc)
        schedule = CardSchedule(
            card_id=card.id,
            fsrs_card_json=card_to_json(fsrs_card),
            state=fsrs_card.state,
            due_at=now,
            last_review_at=None,
        )
        db.add(schedule)

        gen.status = "approved"
        gen.saved_card_id = card.id
        gen.approved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(card)
        return card
    except Exception as e:
        db.rollback()
        gen.status = "failed"
        gen.output = {**gen.output, "_error": str(e)}
        db.commit()
        return None


# ============================================================
# 路由
# ============================================================


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    deck_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档（保存文件 + 创建 Task + 后台解析）"""
    error = validate_file(file.filename or "", file.size or 0)
    if error:
        raise bad_request(error)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4()}{Path(file.filename).suffix.lower()}"
    file_path = str(UPLOAD_DIR / safe_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = SourceDocument(
        user_id=current_user.id,
        filename=file.filename or safe_name,
        file_path=file_path,
        file_type=Path(file.filename).suffix.lstrip(".").lower() or "unknown",
        file_size=len(content),
        status="uploaded",
    )
    db.add(doc)
    db.flush()

    task = AiTask(
        user_id=current_user.id,
        task_type="document_parse",
        deck_id=deck_id,
        source_document_id=doc.id,
        status="processing",
        progress=5,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    doc_id = doc.id
    task_id = task.id

    # 后台线程：只传 ID，所有 DB 操作通过 db2 重新查询
    def _process(task_id: int, doc_id: int, file_path: str, deck_id: int | None):
        db2 = SessionLocal()
        try:
            # 10% → 开始解析
            _t, doc = _get_task_and_doc(db2, task_id, doc_id)
            if _t:
                _t.progress = 10
                db2.commit()

            _, text = parse_file(file_path)

            # 25% → 解析完成
            _t, doc = _get_task_and_doc(db2, task_id, doc_id)
            if doc and text:
                doc.content_text = text[:200000]
                doc.status = "parsed"
            if _t:
                _t.progress = 25
            db2.commit()

            # 如果指定 deck_id，自动 AI 生成卡片
            if deck_id and text:
                # 40% → 准备 AI 生成
                if _t:
                    _t.task_type = "card_generate"
                    _t.progress = 40
                    db2.commit()

                # 55% → AI 生成中（分段）
                _t, _ = _get_task_and_doc(db2, task_id)
                if _t:
                    _t.progress = 55
                    db2.commit()

                cards = generate_cards_from_text(text, max_cards=30)

                # 75% → AI 生成完成，保存中
                _t, _ = _get_task_and_doc(db2, task_id)
                if _t:
                    _t.progress = 75
                _save_generations(db2, task_id, cards)

            # 95% → 收尾
            _t, _ = _get_task_and_doc(db2, task_id)
            if _t:
                _t.progress = 95
                db2.commit()

            # 100% → 全流程结束
            _t, _ = _get_task_and_doc(db2, task_id)
            if _t:
                _t.status = "completed"
                _t.progress = 100
                _t.completed_at = datetime.now(timezone.utc)
            db2.commit()

        except Exception as e:
            try:
                _t, _ = _get_task_and_doc(db2, task_id)
                if _t:
                    _t.status = "failed"
                    _t.error_message = str(e)[:2000]
                    _t.completed_at = datetime.now(timezone.utc)
                db2.commit()
            except Exception:
                db2.rollback()
        finally:
            db2.close()

    _background_task(_process, task_id, doc_id, file_path, deck_id)

    return ok({
        "task_id": task_id,
        "source_document_id": doc_id,
        "filename": doc.filename,
        "status": task.status,
    })


@router.post("/cards/generate")
def generate_cards(
    deck_id: int = Query(...),
    text: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从文本生成卡片（后台线程）"""
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.user_id == current_user.id).first()
    if not deck:
        raise not_found("Deck")

    task = AiTask(
        user_id=current_user.id,
        task_type="card_generate",
        deck_id=deck_id,
        status="processing",
        progress=5,
        input_payload={"text_length": len(text)},
    )
    db.add(task)
    db.commit()
    task_id = task.id
    db.close()

    def _gen(task_id: int, text: str):
        db2 = SessionLocal()
        try:
            cards = generate_cards_from_text(text, max_cards=50)
            _t, _ = _get_task_and_doc(db2, task_id)
            if _t:
                _t.progress = 90
            _save_generations(db2, task_id, cards)
            if _t:
                _t.progress = 100
                _t.status = "completed"
                _t.completed_at = datetime.now(timezone.utc)
            db2.commit()
        except Exception as e:
            try:
                _t, _ = _get_task_and_doc(db2, task_id)
                if _t:
                    _t.status = "failed"
                    _t.error_message = str(e)[:2000]
                    _t.completed_at = datetime.now(timezone.utc)
                db2.commit()
            except Exception:
                pass
        finally:
            db2.close()

    _background_task(_gen, task_id, text)
    return ok({"task_id": task_id})


@router.post("/questions/generate")
def generate_questions_api(
    deck_id: int = Query(...),
    text: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 出题"""
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.user_id == current_user.id).first()
    if not deck:
        raise not_found("Deck")

    task = AiTask(
        user_id=current_user.id,
        task_type="question_generate",
        deck_id=deck_id,
        status="processing",
        progress=5,
    )
    db.add(task)
    db.commit()
    task_id = task.id
    db.close()

    def _gen(task_id: int, text: str):
        db2 = SessionLocal()
        try:
            cards = generate_questions(text)
            _save_generations(db2, task_id, cards)
            _t, _ = _get_task_and_doc(db2, task_id)
            if _t:
                _t.progress = 100
                _t.status = "completed"
                _t.completed_at = datetime.now(timezone.utc)
            db2.commit()
        except Exception as e:
            try:
                _t, _ = _get_task_and_doc(db2, task_id)
                if _t:
                    _t.status = "failed"
                    _t.error_message = str(e)[:2000]
                    _t.completed_at = datetime.now(timezone.utc)
                db2.commit()
            except Exception:
                pass
        finally:
            db2.close()

    _background_task(_gen, task_id, text)
    return ok({"task_id": task_id})


@router.post("/answers/evaluate")
def evaluate_answer_api(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 评分（同步）"""
    question = body.get("question")
    reference_answer = body.get("reference_answer")
    user_answer = body.get("user_answer")
    if not all([question, reference_answer, user_answer]):
        raise bad_request("缺少参数")
    result = evaluate_answer(question, reference_answer, user_answer)
    return ok(result)


@router.get("/tasks/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(AiTask).filter(AiTask.id == task_id, AiTask.user_id == current_user.id).first()
    if not task:
        raise not_found("Task")

    from sqlalchemy import func

    gens = (
        db.query(AiGeneration.status, func.count(AiGeneration.id))
        .filter(AiGeneration.task_id == task.id)
        .group_by(AiGeneration.status)
        .all()
    )

    return ok({
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "error_message": task.error_message,
        "deck_id": task.deck_id,
        "source_document_id": task.source_document_id,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
        "generation_counts": {s: c for s, c in gens},
    })


@router.get("/generations")
def list_generations(
    task_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        db.query(AiGeneration)
        .join(AiTask, AiTask.id == AiGeneration.task_id)
        .filter(AiTask.user_id == current_user.id)
    )
    if task_id:
        q = q.filter(AiGeneration.task_id == task_id)
    if status:
        q = q.filter(AiGeneration.status == status)

    gens = q.order_by(AiGeneration.created_at.desc()).limit(limit).all()
    return ok([
        {
            "id": g.id,
            "task_id": g.task_id,
            "generation_type": g.generation_type,
            "status": g.status,
            "output": g.output,
            "saved_card_id": g.saved_card_id,
            "approved_at": g.approved_at,
            "created_at": g.created_at,
        }
        for g in gens
    ])


@router.post("/generations/{gen_id}/approve")
def approve_generation(
    gen_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gen = (
        db.query(AiGeneration)
        .join(AiTask, AiTask.id == AiGeneration.task_id)
        .filter(AiGeneration.id == gen_id, AiTask.user_id == current_user.id)
        .first()
    )
    if not gen:
        raise not_found("Generation")

    card = _approve_generation(db, gen_id, current_user)
    if not card:
        raise bad_request("保存失败，请检查 generation 数据")

    return ok({"generation_id": gen_id, "card_id": card.id, "status": "approved"})


@router.post("/generations/bulk-approve")
def bulk_approve(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ids: list[int] = body.get("ids", [])
    if not ids:
        raise bad_request("缺少 ids")

    saved = 0
    for gen_id in ids:
        gen = (
            db.query(AiGeneration)
            .join(AiTask, AiTask.id == AiGeneration.task_id)
            .filter(AiGeneration.id == gen_id, AiTask.user_id == current_user.id)
            .first()
        )
        if gen and gen.status == "pending":
            if _approve_generation(db, gen_id, current_user):
                saved += 1

    return ok({"saved": saved})


@router.delete("/generations/{gen_id}")
def reject_generation(
    gen_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gen = (
        db.query(AiGeneration)
        .join(AiTask, AiTask.id == AiGeneration.task_id)
        .filter(AiGeneration.id == gen_id, AiTask.user_id == current_user.id)
        .first()
    )
    if not gen:
        raise not_found("Generation")

    if gen.status != "approved":
        db.delete(gen)
    else:
        gen.status = "rejected"
    db.commit()
    return ok({"deleted": gen_id})


@router.get("/documents")
def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = (
        db.query(SourceDocument)
        .filter(SourceDocument.user_id == current_user.id)
        .order_by(SourceDocument.created_at.desc())
        .limit(limit)
        .all()
    )
    return ok([
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "created_at": d.created_at,
        }
        for d in docs
    ])
