from typing import ClassVar

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".././envs/local.api.env",
        extra="ignore",
    )

    database_url: str
    jwt_secret_key: SecretStr

    @field_validator("database_url")
    @classmethod
    def use_asyncpg(cls, url: str) -> str:
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()  # pyright: ignore[reportCallIssue]
