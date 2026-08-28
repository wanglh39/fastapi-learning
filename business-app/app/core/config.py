"""配置管理：基于 pydantic-settings，多环境支持。

阶段 8.1 实现：
- 从 .env 读取
- 区分 dev/prod/test 环境
- 敏感配置（密钥、DB 密码）不进仓库
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。

    通过环境变量或 .env 文件注入，例如：
        APP_NAME=BlogAPI
        DATABASE_URL=postgresql+asyncpg://user:pass@localhost/blog
        SECRET_KEY=...
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BlogAPI"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite+aiosqlite:///./blog.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"

    log_level: str = "INFO"


settings = Settings()