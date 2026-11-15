"""全局配置 - 从 .env 加载"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # .env 键全大写，字段全小写，不区分大小写匹配
        extra="ignore",
    )

    # ----- 应用 -----
    app_name: str = Field(default="MemoMind")
    app_env: str = Field(default="dev")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:5173")

    # ----- 数据库 -----
    database_url: str = Field(
        default="postgresql+psycopg2://memomind:memomind@localhost:5433/memomind"
    )

    # ----- JWT -----
    jwt_secret_key: str = Field(
        default="dev-secret-key-change-in-production-please-use-openssl-rand-hex-32"
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=10080)  # 7 天

    # ----- AI -----
    ai_provider: str = Field(default="deepseek")
    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    deepseek_model: str = Field(default="deepseek-chat")

    # ----- Redis -----
    redis_url: str = Field(default="redis://localhost:6379/0")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env.lower() in ("prod", "production")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
