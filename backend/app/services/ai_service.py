"""AI 卡片生成 / 评分服务"""
import re
from typing import Any

from ..ai.deepseek import get_ai_provider, AIProviderError
from ..ai.prompts import (
    SYSTEM_CARD_GENERATE,
    SYSTEM_ANSWER_EVAL,
    USER_EVAL_TEMPLATE,
    SYSTEM_QUESTION_GENERATE,
)


def _strip_markdown_headers(text: str) -> str:
    """去掉行首的 Markdown # 标题标记（AI 偶尔会加）"""
    # 逐行去掉行首的 1-6 个 # 后跟空格
    lines = text.split("\n")
    cleaned = [re.sub(r"^\s{0,3}#{1,6}\s*", "", line) for line in lines]
    return "\n".join(cleaned).strip()


def _clean_card_content(cards: list[dict]) -> list[dict]:
    """递归清理卡片 JSON 中所有字符串值的 Markdown 标题标记"""
    def clean_value(v: Any) -> Any:
        if isinstance(v, str):
            return _strip_markdown_headers(v)
        if isinstance(v, dict):
            return {k: clean_value(val) for k, val in v.items()}
        if isinstance(v, list):
            return [clean_value(item) for item in v]
        return v

    return [clean_value(c) for c in cards]


def call_ai_json(system_prompt: str, user_prompt: str, timeout: int = 30) -> dict:
    """通用 AI → JSON 调用费曼/联想等场景都复用这个"""
    provider = get_ai_provider()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    result = provider.chat_json(messages, max_tokens=1024)
    if isinstance(result, list):
        # AI 偶尔包成数组
        return result[0] if result else {}
    return result if isinstance(result, dict) else {}


def generate_cards_from_text(text: str, max_cards: int = 30) -> list[dict[str, Any]]:
    """调用 AI 从文本生成卡片

    返回: 卡片 JSON 数组
    """
    provider = get_ai_provider()

    # 分段处理（避免单次 token 超限）
    chunks = _split_text(text, max_chars=4000)
    all_cards: list[dict] = []

    for chunk in chunks:
        messages = [
            {"role": "system", "content": SYSTEM_CARD_GENERATE},
            {
                "role": "user",
                "content": f"以下是要处理的知识内容，请生成卡片：\n\n{chunk}",
            },
        ]
        try:
            cards = provider.chat_json(messages, max_tokens=8192)
        except AIProviderError as e:
            # 单个 chunk 失败不阻断，记日志后继续
            print(f"[AI] chunk 生成失败: {e}")
            continue

        if isinstance(cards, list):
            all_cards.extend(cards)
        elif isinstance(cards, dict) and "cards" in cards:
            all_cards.extend(cards["cards"])

        if len(all_cards) >= max_cards:
            break

    # 去重（按 front_content 的 content/question/word）
    all_cards = _dedupe_cards(all_cards)
    # 清理 AI 返回内容中的 Markdown # 标题标记
    all_cards = _clean_card_content(all_cards)
    return all_cards[:max_cards]


def evaluate_answer(
    question: str,
    reference_answer: str,
    user_answer: str,
) -> dict:
    """AI 评分用户回答"""
    provider = get_ai_provider()

    messages = [
        {"role": "system", "content": SYSTEM_ANSWER_EVAL},
        {
            "role": "user",
            "content": USER_EVAL_TEMPLATE.format(
                question=question,
                reference_answer=reference_answer,
                user_answer=user_answer,
            ),
        },
    ]
    return provider.chat_json(messages, max_tokens=2048)


def generate_questions(text: str, deck_id: int | None = None) -> list[dict]:
    """AI 从文本生成练习题"""
    provider = get_ai_provider()
    chunks = _split_text(text, max_chars=4000)
    all_items: list[dict] = []

    for chunk in chunks:
        messages = [
            {"role": "system", "content": SYSTEM_QUESTION_GENERATE},
            {"role": "user", "content": f"请针对以下内容出题：\n\n{chunk}"},
        ]
        try:
            items = provider.chat_json(messages, max_tokens=2048)
        except AIProviderError as e:
            print(f"[AI] 出题失败: {e}")
            continue

        if isinstance(items, list):
            all_items.extend(items)
        elif isinstance(items, dict) and "questions" in items:
            all_items.extend(items["questions"])

    return _clean_card_content(_dedupe_cards(all_items))


def _split_text(text: str, max_chars: int = 4000) -> list[str]:
    """按段落切分文本，单段不超过 max_chars"""
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for p in paragraphs:
        if current_len + len(p) + 1 > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(p)
        current_len += len(p) + 1

    if current:
        chunks.append("\n".join(current))

    return chunks


def _dedupe_cards(cards: list[dict]) -> list[dict]:
    """基于 front_content 去重"""
    seen: set[str] = set()
    result: list[dict] = []
    for c in cards:
        fc = c.get("front_content") or {}
        key = fc.get("content") or fc.get("question") or fc.get("word") or str(fc)
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result
