"""DeepSeek AI Provider 实现"""
import json
from typing import Any

import httpx

from .provider import BaseAIProvider, AIProviderError
from ..core.config import settings


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek Chat API 实现

    文档: https://api-docs.deepseek.com/guide/chat_input
    """

    def __init__(self):
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.api_key = settings.deepseek_api_key
        self.model = settings.deepseek_model or "deepseek-chat"
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=httpx.Timeout(60.0))
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: str | None = None,
    ) -> str:
        if not self.api_key:
            raise AIProviderError("DEEPSEEK_API_KEY 未配置")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = {"type": response_format}

        try:
            resp = self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise AIProviderError(f"HTTP error: {e}", raw=str(e)) from e
        except (KeyError, IndexError) as e:
            raise AIProviderError(f"Unexpected response structure: {e}", raw=resp.text) from e

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> dict:
        # 强制要求 JSON 输出
        content = self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json_object",
        )
        parsed = _robust_json_loads(content)
        if parsed is None:
            raise AIProviderError(f"AI 返回无法解析为 JSON: {content[:300]}")
        return parsed


def _robust_json_loads(content: str) -> dict | list | None:
    """尽量从 AI 返回文本中提取 JSON。AI 有时会在 JSON 前后加说明文字、
    或者返回多个 JSON 拼接、或者包在 markdown code block 里。"""
    text = content.strip()

    # 1. markdown code block
    if "```" in text:
        import re
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()

    # 2. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. 尝试用 JSONDecoder 拿第一个完整 JSON（解决 "Extra data" 多个拼接的情况）
    try:
        decoder = json.JSONDecoder()
        obj, _end = decoder.raw_decode(text)
        return obj
    except json.JSONDecodeError:
        pass

    # 4. 数组 fallback
    arr_start = text.find("[")
    arr_end = text.rfind("]")
    if arr_start >= 0 and arr_end > arr_start:
        try:
            return json.loads(text[arr_start : arr_end + 1])
        except json.JSONDecodeError:
            pass

    # 5. 对象 fallback
    obj_start = text.find("{")
    obj_end = text.rfind("}")
    if obj_start >= 0 and obj_end > obj_start:
        try:
            return json.loads(text[obj_start : obj_end + 1])
        except json.JSONDecodeError:
            pass

    return None


def get_ai_provider() -> BaseAIProvider:
    """工厂函数：根据配置返回 AI Provider 实例"""
    provider_name = (settings.ai_provider or "deepseek").lower()
    if provider_name == "deepseek":
        return DeepSeekProvider()
    # 预留：dashscope 等
    raise AIProviderError(f"Unknown AI provider: {provider_name}")
