"""AI Provider 抽象基类"""
from abc import ABC, abstractmethod
from typing import Any


class AIProviderError(Exception):
    """AI 调用异常"""

    def __init__(self, message: str, raw: Any = None):
        super().__init__(message)
        self.raw = raw


class BaseAIProvider(ABC):
    """AI Provider 统一接口"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: str | None = None,  # 如 "json_object"
    ) -> str:
        """调用 chat completion，返回文本内容"""
        ...

    @abstractmethod
    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> dict:
        """调用并强制返回 JSON，自动解析"""
        ...
