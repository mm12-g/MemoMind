"""文档解析 - PDF / DOCX / TXT / Markdown → 纯文本"""
import os
from pathlib import Path


ALLOWED_EXT = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def parse_file(file_path: str) -> tuple[str, str]:
    """解析文件，返回 (file_type, 纯文本内容)

    不识别的类型返回 ("unknown", "")
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return ("pdf", _parse_pdf(file_path))
    if ext == ".docx":
        return ("docx", _parse_docx(file_path))
    if ext in (".txt", ".md"):
        return (ext.lstrip("."), _parse_text(file_path))
    return ("unknown", "")


def _parse_pdf(path: str) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    try:
        parts = []
        for page in doc:
            parts.append(page.get_text())
        return "\n".join(parts)
    finally:
        doc.close()


def _parse_docx(path: str) -> str:
    from docx import Document

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _parse_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def validate_file(filename: str, size: int) -> str | None:
    """校验文件是否允许，返回错误信息（None 表示通过）"""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return f"不支持的文件类型 {ext}，支持: {', '.join(sorted(ALLOWED_EXT))}"
    if size > MAX_FILE_SIZE:
        return f"文件过大（{size / 1024 / 1024:.1f}MB），限制 10MB"
    return None
